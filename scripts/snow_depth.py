"""Build the Nordmarka snow-depth data for the site.

Reads snow depth from the seNorge snow model (NVE and MET Norway) for two
points: the forest edge at Sognsvann and the deep forest at Kikutstua. The
model gives today's estimate plus a forecast about nine days ahead, driven by
MET's weather forecast. Writes a small JSON file the site reads. Runs on a
schedule in GitHub Actions.

Usage: python scripts/snow_depth.py <output.json>
Standard library only.
"""
from __future__ import annotations

import json
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

OSLO = ZoneInfo("Europe/Oslo")
DAYS = 10  # today plus nine; the model has no values further out
# 1 km grid cells in UTM zone 33 (EUREF89). "altitude" is the cell's average height.
POINTS = [
    {"id": "edge", "name": "Sognsvann", "label": "Forest edge", "x": 262000, "y": 6656000},
    {"id": "deep", "name": "Kikutstua", "label": "Deep in the Marka", "x": 258000, "y": 6668000},
]
GTS_URL = "https://gts.nve.no/api/GridTimeSeries/{x}/{y}/{start}/{end}/{theme}.json"
USER_AGENT = "oslobiketours.no snow-depth post@oslobiketours.no"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(2):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except Exception:
            if attempt == 1:
                raise
            time.sleep(5)


def series(point: dict, theme: str, start: date, end: date) -> tuple[list, int]:
    """Daily values from start to end (the model's day ends 06:00 UTC); None where it has no data."""
    data = fetch_json(GTS_URL.format(x=point["x"], y=point["y"], start=start, end=end, theme=theme))
    return [None if v == data["NoDataValue"] else v for v in data["Data"]], data["Altitude"]


def point_days(point: dict, today: date) -> dict:
    end = today + timedelta(days=DAYS - 1)
    depth, altitude = series(point, "sd", today, end)
    new, _ = series(point, "fsw", today, end)
    days = []
    for i, cm in enumerate(depth):
        if cm is None:
            break
        days.append({
            "date": (today + timedelta(days=i)).isoformat(),
            "depth_cm": round(cm),
            "new_snow_mm": new[i] if i < len(new) and new[i] is not None else 0,  # water equivalent
        })
    return {"id": point["id"], "name": point["name"], "label": point["label"],
            "altitude": altitude, "days": days}


def build(now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    today = now.astimezone(OSLO).date()
    return {
        "generated": now.isoformat(timespec="minutes"),
        "points": [point_days(p, today) for p in POINTS],
        "source": "seNorge snow model, NVE and MET Norway, CC BY 4.0",
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: snow_depth.py <output.json>")
    data = build()
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    for p in data["points"]:
        print(p["name"], f'{p["altitude"]} m:', " ".join(f'{d["depth_cm"]}' for d in p["days"]), "cm")
