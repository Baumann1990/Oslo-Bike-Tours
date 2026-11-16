"""Write a plain-HTML summary of the riding forecast into the conditions page.

The page fills its live panels with JavaScript, which most AI crawlers never run.
This puts the same forecast into the HTML itself at deploy time, so search engines
and AI tools see real, current conditions. The page's script hides it once the
live panels have loaded.

Usage: python scripts/conditions_snapshot.py <conditions.json> <page.html> [snow.json]
Standard library only.
"""
from __future__ import annotations

import html
import json
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

# The season switch lives in main.js; while closed, days are described as weather, not riding.
MAIN_JS = Path(__file__).resolve().parent.parent / "js" / "main.js"
CLOSED = bool(re.search(r"const SEASON_CLOSED = true", MAIN_JS.read_text(encoding="utf-8")))
LEVEL = ({"good": "Dry", "showers": "Showers", "windy": "Windy", "wet": "Rain", "snow": "Snow"} if CLOSED else
         {"good": "Good riding", "showers": "Showers", "windy": "Windy", "wet": "Wet", "snow": "Snow"})
# Riding time per route, stops included (same as the page's script).
ROUTES = [("Maridalen and the lake", 2), ("The short forest loop", 2), ("The Nordmarka loop", 3),
          ("Ring 4", 5), ("Into the deep Marka", 6)]
START, END = "<!--SNAPSHOT-->", "<!--/SNAPSHOT-->"


def day_line(d: dict) -> str:
    when = date.fromisoformat(d["date"])
    deg = lambda t: f"−{-t}" if t < 0 else f"{t}"  # true minus sign; "to" because a dash reads as one
    temp = f'{deg(d["temp_max"])} °C' if d["temp_min"] == d["temp_max"] else f'{deg(d["temp_min"])} to {deg(d["temp_max"])} °C'
    rain = f'{d["precip"]} mm {"snow" if d["level"] == "snow" else "rain"}' if d["precip"] > 0 else "dry"
    outlook = " (outlook)" if d.get("outlook") else ""
    return (f'<li><strong>{when:%A} {when.day} {when:%B}{outlook}: {LEVEL[d["level"]]}</strong>. '
            f'{temp}, {rain}, wind up to {d["wind_max"]} m/s, sunset {d["sunset"]}.</li>')


def latest_starts(d: dict) -> str:
    end = datetime.fromisoformat(d["end"])
    parts = []
    for name, hours in ROUTES:
        t = end - timedelta(hours=hours)
        t = t.replace(minute=t.minute // 15 * 15)
        parts.append(f"{name} {t:%H:%M}" if t.hour >= 10 else f"{name} too long for the daylight")
    return "; ".join(parts)


def snow_line(snow: dict | None) -> str:
    """Today's snow depth at both points, if there is any to report."""
    if not snow:
        return ""
    points = {p["id"]: p for p in snow.get("points", []) if p.get("days")}
    edge, deep = points.get("edge"), points.get("deep")
    if not edge or not deep:
        return ""
    e, d = edge["days"][0]["depth_cm"], deep["days"][0]["depth_cm"]
    if not CLOSED and not e and not d:
        return ""
    return (f'<p>Snow depth this morning: {e} cm at {edge["name"]} on the forest edge ({edge["altitude"]} m) '
            f'and {d} cm at {deep["name"]} deeper in the Marka ({deep["altitude"]} m), '
            f'from the seNorge snow model by NVE and MET Norway.</p>')


def snapshot(data: dict, snow: dict | None = None) -> str:
    days = [d for d in data.get("days", []) if d.get("level") in LEVEL]
    if not days:
        return snow_line(snow) and f'<div class="cx-snapshot" id="cxSnapshot">{snow_line(snow)}</div>'
    generated = datetime.fromisoformat(data["generated"]).astimezone(ZoneInfo("Europe/Oslo"))
    first = days[0]
    starts = ('' if CLOSED else
              f'<p>Latest start to finish in daylight on {date.fromisoformat(first["date"]):%A}: '
              f'{html.escape(latest_starts(first))}.</p>')
    return (
        '<div class="cx-snapshot" id="cxSnapshot">'
        f'{snow_line(snow)}'
        f'<p>Nordmarka forecast as of {generated.day} {generated:%B %Y, %H:%M} Oslo time, for the hours from 10:00 to sunset:</p>'
        f'<ul>{"".join(day_line(d) for d in days)}</ul>'
        f'{starts}'
        '</div>'
    )


def main(json_path: str, page_path: str, snow_path: str | None = None) -> None:
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    snow = None
    if snow_path:
        try:
            with open(snow_path, encoding="utf-8") as fh:
                snow = json.load(fh)
        except (OSError, ValueError):
            pass  # the snow step failed; the weather snapshot still goes out
    with open(page_path, encoding="utf-8") as fh:
        page = fh.read()
    head, rest = page.split(START, 1)
    _, tail = rest.split(END, 1)
    page = head + START + snapshot(data, snow) + END + tail
    page = page.replace('"dateModified": ""', f'"dateModified": "{data["generated"]}"')
    with open(page_path, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("snapshot written for", len(data.get("days", [])), "days")


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit("usage: conditions_snapshot.py <conditions.json> <page.html> [snow.json]")
    main(*sys.argv[1:])
