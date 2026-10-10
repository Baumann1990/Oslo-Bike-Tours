"""Fetch Norges Bank's official NOK exchange rates for the site's price converter.

Writes a small JSON file with how many NOK one EUR, USD and GBP cost, so the
rental page can show approximate prices in a visitor's own currency.
Runs on a schedule in GitHub Actions.

Usage: python scripts/exchange_rates.py <output.json>
Standard library only.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone

CURRENCIES = ("EUR", "USD", "GBP")
URL = ("https://data.norges-bank.no/api/data/EXR/B." + "+".join(CURRENCIES)
       + ".NOK.SP?format=sdmx-json&lastNObservations=1&locale=en")


def build() -> dict:
    req = urllib.request.Request(URL, headers={"User-Agent": "oslobiketours.no price-converter"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)["data"]

    dims = data["structure"]["dimensions"]
    series_dims = dims["series"]
    base_pos = next(i for i, d in enumerate(series_dims) if d["id"] == "BASE_CUR")
    base_ids = [v["id"] for v in series_dims[base_pos]["values"]]
    obs_date = dims["observation"][0]["values"][-1]["id"]

    mult_attr = next((i for i, a in enumerate(data["structure"]["attributes"]["series"])
                      if a["id"] == "UNIT_MULT"), None)
    mult_values = (data["structure"]["attributes"]["series"][mult_attr]["values"]
                   if mult_attr is not None else [])

    rates = {}
    for key, series in data["dataSets"][0]["series"].items():
        currency = base_ids[int(key.split(":")[base_pos])]
        value = float(next(iter(series["observations"].values()))[0])
        if mult_attr is not None:  # e.g. rates quoted per 100 units
            value /= 10 ** int(mult_values[series["attributes"][mult_attr]]["id"])
        rates[currency] = round(value, 4)

    missing = set(CURRENCIES) - set(rates)
    if missing:
        raise ValueError(f"Norges Bank returned no rate for {sorted(missing)}")
    return {
        "generated": datetime.now(timezone.utc).isoformat(timespec="minutes"),
        "date": obs_date,
        "nok_per": rates,
        "source": "Norges Bank",
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: exchange_rates.py <output.json>")
    out = build()
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(out["date"], out["nok_per"])
