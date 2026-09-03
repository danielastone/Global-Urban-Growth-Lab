"""Build a deterministic, non-committed UNSD census-date staging table."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from urban_growth.unsd_census_dates import (
    UNSD_TO_M49_ALIASES,
    build_census_assertions,
    build_country_crosswalk,
    census_assertions_csv_bytes,
    parse_m49_countries,
    parse_raw_census_cells,
    require_expected_exceptions,
)

CENSUS_SOURCE_ID = "unsd_census_dates_2026_02_03"
CENSUS_RELEASE = "Last updated 03 February 2026"
CENSUS_SHA256 = "900b7f3691efe2c1309e422b16816e5ed45ebb127a7e71db3443f987fccf6165"
CENSUS_SNAPSHOT_ID = f"{CENSUS_SOURCE_ID}:{CENSUS_SHA256}"
M49_SHA256 = "b9048114f6e7f2abda83bf03d4263c9d7cd1bd7230e3d0461025ee7839a7a1fb"


def _verified_text(path: Path, expected_sha256: str) -> str:
    payload = path.read_bytes()
    actual = hashlib.sha256(payload).hexdigest()
    if actual != expected_sha256:
        raise ValueError(f"{path} checksum mismatch: expected {expected_sha256}, got {actual}")
    return payload.decode("utf-8")


def build_output(
    *,
    census_html_path: Path,
    m49_html_path: Path,
    allowed_unmatched: set[str],
    allowed_unparsed: set[str],
) -> bytes:
    census_html = _verified_text(census_html_path, CENSUS_SHA256)
    m49_html = _verified_text(m49_html_path, M49_SHA256)
    cells = parse_raw_census_cells(census_html)
    m49 = parse_m49_countries(m49_html)
    names = sorted({row.source_country_name for row in cells})
    crosswalk = build_country_crosswalk(names, m49, aliases=UNSD_TO_M49_ALIASES)
    assertions = build_census_assertions(cells, crosswalk)
    require_expected_exceptions(
        assertions,
        allowed_unmatched=allowed_unmatched,
        allowed_unparsed=allowed_unparsed,
    )
    return census_assertions_csv_bytes(
        assertions,
        source_id=CENSUS_SOURCE_ID,
        source_release=CENSUS_RELEASE,
        snapshot_id=CENSUS_SNAPSHOT_ID,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--census-html", type=Path, required=True)
    parser.add_argument("--m49-html", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--allow-unmatched", action="append", default=[])
    parser.add_argument("--allow-unparsed", action="append", default=[])
    args = parser.parse_args()

    payload = build_output(
        census_html_path=args.census_html,
        m49_html_path=args.m49_html,
        allowed_unmatched=set(args.allow_unmatched),
        allowed_unparsed=set(args.allow_unparsed),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(payload)
    print(
        json.dumps(
            {
                "output_path": args.output.as_posix(),
                "bytes": len(payload),
                "sha256": hashlib.sha256(payload).hexdigest(),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
