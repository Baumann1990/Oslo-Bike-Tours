"""Build the Nordmarka riding-conditions data for the site.

Scores the riding day (10:00 to sunset, when bikes can be collected) from
MET Norway's forecast for a point near Ullevålseter in the middle of the
Nordmarka, and writes a small JSON file the site reads. Runs on a schedule
in GitHub Actions.

Usage: python scripts/riding_forecast.py <output.json>
Standard library only.
"""
from __future__ import annotations

import json
import math
import sys
import time
import urllib.request
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LAT, LON = 60.0230, 10.7000  # near Ullevålseter (MET asks for max 4 decimals)
OSLO = ZoneInfo("Europe/Oslo")
DAYS = 4
OPEN_HOUR = 10      # bikes can be collected from 10:00
MIN_HOURS_LEFT = 2  # skip today once less riding daylight than this remains

MET_URL = f"https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={LAT}&lon={LON}"
SUN_URL = f"https://api.met.no/weatherapi/sunrise/3.0/sun?lat={LAT}&lon={LON}"
# MET Norway's terms require an identifying User-Agent.
USER_AGENT = "oslobiketours.no riding-conditions post@oslobiketours.no"


def fetch_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception:
            if attempt == 1:
                raise
            time.sleep(5)


def sun_elevation(when: datetime) -> float:
    """Approximate solar elevation in degrees (NOAA general solar position formulae)."""
    t = when.astimezone(timezone.utc)
    hour = t.hour + t.minute / 60
    g = 2 * math.pi / 365 * (t.timetuple().tm_yday - 1 + (hour - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g)
            - 0.006758 * math.cos(2 * g) + 0.000907 * math.sin(2 * g)
            - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    solar_minutes = hour * 60 + eqtime + 4 * LON
    hour_angle = math.radians(solar_minutes / 4 - 180)
    lat = math.radians(LAT)
    cos_zenith = (math.sin(lat) * math.sin(decl)
                  + math.cos(lat) * math.cos(decl) * math.cos(hour_angle))
    return 90 - math.degrees(math.acos(max(-1.0, min(1.0, cos_zenith))))


def sunset_estimate(day: date) -> datetime:
    """Fallback: first minute after midday when the sun's upper edge drops below the horizon."""
    t = datetime(day.year, day.month, day.day, 12, 0, tzinfo=OSLO)
    while sun_elevation(t) > -0.833 and t.hour < 23:
        t += timedelta(minutes=1)
    return t


def sunset(day: date) -> datetime:
    """Sunset from MET Norway's sunrise service; our own estimate (within a few minutes) if it fails."""
    offset = datetime(day.year, day.month, day.day, 12, tzinfo=OSLO).strftime("%z")
    url = f"{SUN_URL}&date={day.isoformat()}&offset={offset[:3]}:{offset[3:]}"
    try:
        return datetime.fromisoformat(fetch_json(url)["properties"]["sunset"]["time"]).astimezone(OSLO)
    except Exception:
        return sunset_estimate(day)


def hourly(series: list) -> dict[datetime, dict]:
    """Per-hour precipitation, symbol and temperature.

    MET gives hourly steps for roughly the next 2.5 days, then 6-hourly ones;
    a 6-hour block is spread evenly over its hours where no hourly data exists.
    """
    hours: dict[datetime, dict] = {}
    spread: dict[datetime, dict] = {}
    for step in series:
        ts = datetime.fromisoformat(step["time"].replace("Z", "+00:00"))
        data = step["data"]
        temp = data["instant"]["details"].get("air_temperature")
        wind = data["instant"]["details"].get("wind_speed")
        if "next_1_hours" in data:
            nxt = data["next_1_hours"]
            hours[ts] = {
                "precip": nxt.get("details", {}).get("precipitation_amount", 0.0),
                "symbol": nxt.get("summary", {}).get("symbol_code", ""),
                "temp": temp, "wind": wind,
            }
        elif "next_6_hours" in data:
            nxt = data["next_6_hours"]
            amount = nxt.get("details", {}).get("precipitation_amount", 0.0)
            symbol = nxt.get("summary", {}).get("symbol_code", "")
            for i in range(6):
                spread[ts + timedelta(hours=i)] = {
                    "precip": amount / 6, "symbol": symbol,
                    "temp": temp if i == 0 else None, "wind": wind if i == 0 else None,
                }
    for ts, row in spread.items():
        hours.setdefault(ts, row)
    return hours


def classify(rows: list[dict], precip: float, temp_max: float, wind_max: float) -> str:
    # Nordmarka gravel drains well, so rain is "wet", never a reason not to ride.
    # Only MET's snow forecasts count as snow. Its in-between rain-and-snow category
    # is often just cold rain on the day, so it is scored as rain. One snowy hour
    # does not make a snowy day: it has to carry real precipitation or a good
    # share of the riding window.
    snow = [r for r in rows if r["precip"] > 0 and "snow" in r["symbol"]]
    if sum(r["precip"] for r in snow) >= 1.0 or len(snow) >= max(2, len(rows) / 3):
        return "snow"
    if precip >= 3 or any("heavyrain" in r["symbol"] or "heavysleet" in r["symbol"] for r in rows):
        return "wet"
    if precip >= 0.5:
        return "showers"
    if wind_max >= 15:
        return "windy"
    return "good"


def score_day(day: date, hours: dict, now: datetime) -> dict | None:
    start = datetime(day.year, day.month, day.day, OPEN_HOUR, tzinfo=OSLO)
    end = sunset(day)
    if day == now.astimezone(OSLO).date():
        start = max(start, now.astimezone(OSLO).replace(minute=0, second=0, microsecond=0))
        if end - start < timedelta(hours=MIN_HOURS_LEFT):
            return None

    rows = [r for ts, r in hours.items() if start <= ts < end]
    entry = {
        "date": day.isoformat(),
        "start": start.isoformat(),
        "end": end.isoformat(),
        "sunset": end.strftime("%H:%M"),
        "level": None,
    }
    if not rows:
        return entry

    temps = [r["temp"] for r in rows if r["temp"] is not None]
    winds = [r["wind"] for r in rows if r["wind"] is not None]
    if not temps:  # 6-hourly days can have no instant inside a short window
        near = [r for ts, r in hours.items() if start - timedelta(hours=3) <= ts < end + timedelta(hours=3)]
        temps = [r["temp"] for r in near if r["temp"] is not None]
        winds = winds or [r["wind"] for r in near if r["wind"] is not None]
    if not temps:
        return entry

    precip = sum(r["precip"] for r in rows)
    temp_max, wind_max = max(temps), max(winds) if winds else 0.0
    entry.update({
        "temp_max": round(temp_max),
        "temp_min": round(min(temps)),
        "precip": round(precip, 1),
        "wind_max": round(wind_max),
        "level": classify(rows, precip, temp_max, wind_max),
    })
    return entry


def first_snow(hours: dict) -> str | None:
    """Earliest date in the whole forecast with snow (not rain-and-snow), so we know when to revert autumn rates."""
    for ts in sorted(hours):
        if hours[ts]["precip"] > 0 and "snow" in hours[ts]["symbol"]:
            return ts.astimezone(OSLO).date().isoformat()
    return None


def build(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    hours = hourly(fetch_json(MET_URL)["properties"]["timeseries"])
    today = now.astimezone(OSLO).date()
    days = [score_day(today + timedelta(days=i), hours, now) for i in range(DAYS + 1)]
    return {
        "generated": now.isoformat(timespec="minutes"),
        "location": "Nordmarka (near Ullevålseter)",
        "days": [d for d in days if d is not None][:DAYS],
        "first_snow": first_snow(hours),
        "source": "MET Norway, CC BY 4.0",
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: riding_forecast.py <output.json>")
    data = build()
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    for d in data["days"]:
        print(d["date"], d["level"], d.get("temp_max"), "°C", d.get("precip"), "mm",
              "wind", d.get("wind_max"), "sunset", d["sunset"])
    print("first snow in forecast:", data["first_snow"])
