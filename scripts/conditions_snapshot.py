"""Write a plain-HTML summary of the riding forecast into the conditions page.

The page fills its live panels with JavaScript, which most AI crawlers never run.
This puts the same forecast into the HTML itself at deploy time, so search engines
and AI tools see real, current conditions. The page's script hides it once the
live panels have loaded.

Usage: python scripts/conditions_snapshot.py <conditions.json> <page.html>
Standard library only.
"""
from __future__ import annotations

import html
import json
import sys
from datetime import date, datetime, timedelta

LEVEL = {"good": "Good riding", "showers": "Showers", "windy": "Windy", "wet": "Wet", "snow": "Snow"}
# Riding time per route, stops included (same as the page's script).
ROUTES = [("Maridalen and the lake", 2), ("The short forest loop", 2), ("The Nordmarka loop", 3),
          ("Ring 4", 5), ("Into the deep Marka", 6)]
START, END = "<!--SNAPSHOT-->", "<!--/SNAPSHOT-->"


def day_line(d: dict) -> str:
    when = date.fromisoformat(d["date"])
    temp = f'{d["temp_max"]} °C' if d["temp_min"] == d["temp_max"] else f'{d["temp_min"]}–{d["temp_max"]} °C'
    rain = f'{d["precip"]} mm rain' if d["precip"] > 0 else "dry"
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


def snapshot(data: dict) -> str:
    days = [d for d in data.get("days", []) if d.get("level") in LEVEL]
    if not days:
        return ""
    generated = datetime.fromisoformat(data["generated"])
    first = days[0]
    return (
        '<div class="cx-snapshot" id="cxSnapshot">'
        f'<p>Nordmarka forecast as of {generated:%d %B %Y, %H:%M} UTC, for the riding hours from 10:00 to sunset:</p>'
        f'<ul>{"".join(day_line(d) for d in days)}</ul>'
        f'<p>Latest start to finish in daylight on {date.fromisoformat(first["date"]):%A}: '
        f'{html.escape(latest_starts(first))}.</p>'
        '</div>'
    )


def main(json_path: str, page_path: str) -> None:
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    with open(page_path, encoding="utf-8") as fh:
        page = fh.read()
    head, rest = page.split(START, 1)
    _, tail = rest.split(END, 1)
    page = head + START + snapshot(data) + END + tail
    page = page.replace('"dateModified": ""', f'"dateModified": "{data["generated"]}"')
    with open(page_path, "w", encoding="utf-8") as fh:
        fh.write(page)
    print("snapshot written for", len(data.get("days", [])), "days")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: conditions_snapshot.py <conditions.json> <page.html>")
    main(sys.argv[1], sys.argv[2])
