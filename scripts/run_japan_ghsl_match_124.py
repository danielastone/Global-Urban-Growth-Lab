"""Run the matched Japan direct-count/GHS-POP construction-smoothing benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from urban_growth.construction_smoothing import compare_direct_counts_with_ghsl
from urban_growth.japan_did import (
    audit_adjacent_did_overlap,
    build_did_direct_count_denominator,
    build_matched_ghsl_intervals,
    read_official_did_archives,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--did-dir", type=Path, default=Path("data/raw/japan_did"))
    parser.add_argument("--ghsl-dir", type=Path, default=Path("data/raw/japan_ghsl_pop"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/japan_ghsl_match_124"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    panel = read_official_did_archives(args.did_dir)
    audit = audit_adjacent_did_overlap(panel)
    rules = ["dynamic_identity_resolved", "strict_stable_resolved"]
    direct_frames = [
        build_did_direct_count_denominator(audit, resolution_column=rule) for rule in rules
    ]
    direct = pd.concat(direct_frames, ignore_index=True)
    direct.to_csv(args.output_dir / "direct_count_origin_denominator.csv", index=False)

    coverage_frames = []
    metric_frames = []
    contrast_frames = []
    ghsl_frames = []
    for rule, rule_direct in zip(rules, direct_frames, strict=True):
        for boundary_mode in ["fixed_origin_did", "dynamic_did"]:
            ghsl = build_matched_ghsl_intervals(
                panel, rule_direct, args.ghsl_dir, boundary_mode=boundary_mode
            )
            coverage, metrics, contrasts = compare_direct_counts_with_ghsl(rule_direct, ghsl)
            for frame in [ghsl, coverage, metrics, contrasts]:
                frame.insert(0, "concordance_rule", rule)
            ghsl_frames.append(ghsl)
            coverage_frames.append(coverage)
            metric_frames.append(metrics)
            contrast_frames.append(contrasts)
    outputs = {
        "ghsl_matched_origin_denominator.csv": pd.concat(ghsl_frames, ignore_index=True),
        "denominator_coverage.csv": pd.concat(coverage_frames, ignore_index=True),
        "matched_source_metrics.csv": pd.concat(metric_frames, ignore_index=True),
        "ghsl_minus_direct_contrasts.csv": pd.concat(contrast_frames, ignore_index=True),
    }
    for name, frame in outputs.items():
        frame.to_csv(args.output_dir / name, index=False)
        print(args.output_dir / name)


if __name__ == "__main__":
    main()
