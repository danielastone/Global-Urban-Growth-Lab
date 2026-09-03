"""Run or fail closed on the direct-count/GHSL construction-smoothing benchmark."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from urban_growth.china_census_124 import (
    china_issue_124_source_register,
    qualify_china_issue_124_sources,
)
from urban_growth.construction_smoothing import compare_direct_counts_with_ghsl
from urban_growth.india_census_124 import (
    india_issue_124_source_register,
    qualify_india_issue_124_sources,
)
from urban_growth.io import SourceSchemaError


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--direct-input", type=Path)
    parser.add_argument("--ghsl-input", type=Path)
    parser.add_argument("--pilot", choices=["us", "india", "china"], default="us")
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/construction_smoothing_124"))
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.pilot == "india":
        register, status = qualify_india_issue_124_sources(india_issue_124_source_register())
        register.to_csv(args.output_dir / "india_source_qualification.csv", index=False)
        status.to_csv(args.output_dir / "india_benchmark_status.csv", index=False)
        print(status.to_csv(index=False))
        return
    if args.pilot == "china":
        register, status = qualify_china_issue_124_sources(china_issue_124_source_register())
        register.to_csv(args.output_dir / "china_source_qualification.csv", index=False)
        status.to_csv(args.output_dir / "china_benchmark_status.csv", index=False)
        print(status.to_csv(index=False))
        return

    status = {
        "issue": 124,
        "pilot": "US Census places",
        "registered_direct_count_waves": "2010;2020",
        "registered_direct_count_intervals": 1,
        "minimum_forecast_origins_required": 2,
        "benchmark_estimable": False,
        "h1_independent_confirmation": False,
        "decision": "unresolved_pending_third_direct_count_wave_and_official_concordance",
    }
    if args.direct_input and args.ghsl_input:
        try:
            coverage, metrics, contrasts = compare_direct_counts_with_ghsl(
                pd.read_csv(args.direct_input), pd.read_csv(args.ghsl_input)
            )
        except SourceSchemaError as exc:
            status["decision"] = str(exc)
        else:
            coverage.to_csv(args.output_dir / "denominator_coverage.csv", index=False)
            metrics.to_csv(args.output_dir / "matched_source_metrics.csv", index=False)
            contrasts.to_csv(args.output_dir / "ghsl_minus_direct_contrasts.csv", index=False)
            status["benchmark_estimable"] = True
            status["decision"] = "interpret_registered_contrasts"
    pd.DataFrame([status]).to_csv(args.output_dir / "benchmark_status.csv", index=False)
    print(pd.DataFrame([status]).to_csv(index=False))


if __name__ == "__main__":
    main()
