"""Run the chronological Japan direct-count hierarchy benchmark for issue 191."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_growth.japan_did import (
    H1_YEARS,
    audit_adjacent_did_overlap,
    build_did_direct_count_denominator,
    read_official_did_archives,
)
from urban_growth.japan_h1 import run_japan_h1_hierarchy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--did-dir", type=Path, default=Path("data/raw/japan_did"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/japan_h1_191"))
    parser.add_argument("--bootstrap-draws", type=int, default=2_000)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    panel = read_official_did_archives(args.did_dir, years=H1_YEARS)
    audit = audit_adjacent_did_overlap(panel, years=H1_YEARS)
    denominators = {
        rule: build_did_direct_count_denominator(
            audit, resolution_column=rule, years=H1_YEARS
        )
        for rule in ["dynamic_identity_resolved", "strict_stable_resolved"]
    }
    coverage, predictions, metrics, contrasts, decision = run_japan_h1_hierarchy(
        denominators, draws=args.bootstrap_draws
    )
    outputs = {
        "denominator_coverage.csv": coverage,
        "chronological_predictions.csv": predictions,
        "chronological_metrics.csv": metrics,
        "registered_gate_contrasts.csv": contrasts,
        "decision.csv": decision,
    }
    for name, frame in outputs.items():
        path = args.output_dir / name
        frame.to_csv(path, index=False)
        print(path)


if __name__ == "__main__":
    main()
