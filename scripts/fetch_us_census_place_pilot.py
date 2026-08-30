"""Acquire official U.S. Census place inputs for the 2010-2020 pilot."""

from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

STATE_FIPS = [
    "01",
    "02",
    "04",
    "05",
    "06",
    "08",
    "09",
    "10",
    "11",
    "12",
    "13",
    "15",
    "16",
    "17",
    "18",
    "19",
    "20",
    "21",
    "22",
    "23",
    "24",
    "25",
    "26",
    "27",
    "28",
    "29",
    "30",
    "31",
    "32",
    "33",
    "34",
    "35",
    "36",
    "37",
    "38",
    "39",
    "40",
    "41",
    "42",
    "44",
    "45",
    "46",
    "47",
    "48",
    "49",
    "50",
    "51",
    "53",
    "54",
    "55",
    "56",
]
QUERIES = {
    2010: ("https://api.census.gov/data/2010/dec/sf1", "P001001"),
    2020: ("https://api.census.gov/data/2020/dec/pl", "P1_001N"),
}
RELATIONSHIP_URL = (
    "https://www2.census.gov/geo/docs/maps-data/data/rel2020/place/tab20_place20_place10_natl.txt"
)


def fetch_json(url: str) -> list[list[str]]:
    with urlopen(url, timeout=60) as response:
        return json.load(response)


def main() -> None:
    key = os.environ.get("CENSUS_API_KEY")
    if not key:
        raise SystemExit("CENSUS_API_KEY is required; do not commit it")
    raw = Path("data/raw")
    raw.mkdir(parents=True, exist_ok=True)
    for year, (endpoint, variable) in QUERIES.items():
        combined: list[list[str]] = []
        for state in STATE_FIPS:
            query = urlencode(
                {
                    "get": f"NAME,{variable}",
                    "for": "place:*",
                    "in": f"state:{state}",
                    "key": key,
                }
            )
            payload = fetch_json(f"{endpoint}?{query}")
            if not combined:
                combined.append(payload[0])
            if payload[0] != combined[0]:
                raise RuntimeError("Census API schema changed across states")
            combined.extend(payload[1:])
        output = raw / f"us_census_{year}_place_population.json"
        output.write_text(json.dumps(combined), encoding="utf-8")
        print(output)
    relationship = raw / "tab20_place20_place10_natl.txt"
    with urlopen(RELATIONSHIP_URL, timeout=60) as response:
        relationship.write_bytes(response.read())
    print(relationship)


if __name__ == "__main__":
    main()
