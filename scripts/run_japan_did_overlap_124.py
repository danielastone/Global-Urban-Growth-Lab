"""Audit Japan DID crosswave coverage and build direct-count persistence intervals."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from urban_growth.japan_did import (
    audit_adjacent_did_overlap,
    build_did_direct_count_intervals,
    did_overlap_coverage,
    direct_count_persistence_diagnostics,
    read_official_did_archives,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=Path("data/raw/japan_did"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/japan_did_124"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    panel = read_official_did_archives(args.raw_dir)
    audit = audit_adjacent_did_overlap(panel)
    coverage = did_overlap_coverage(audit)
    interval_frames = []
    for rule in ["dynamic_identity_resolved", "strict_stable_resolved"]:
        intervals = build_did_direct_count_intervals(audit, resolution_column=rule)
        if not intervals.empty:
            interval_frames.append(intervals)
    if not interval_frames:
        raise RuntimeError("No Japan DID direct-count intervals resolved")
    direct = pd.concat(interval_frames, ignore_index=True)
    diagnostics = direct_count_persistence_diagnostics(direct)

    outputs = {
        "did_overlap_audit.csv": audit,
        "did_overlap_coverage.csv": coverage,
        "did_direct_count_intervals.csv": direct,
        "did_direct_count_persistence.csv": diagnostics,
    }
    for name, frame in outputs.items():
        path = args.output_dir / name
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()
