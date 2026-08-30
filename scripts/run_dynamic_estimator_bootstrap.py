"""Fit the locked dynamic hierarchy and multiplier-bootstrap its uncertainty."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from urban_growth.dynamic_estimators import (
    bootstrap_dynamic_hierarchy,
    common_dynamic_sample,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--outcome", required=True)
    parser.add_argument("--lagged-outcome", required=True)
    parser.add_argument("--covariate", action="append", default=[])
    parser.add_argument("--city", default="city_id")
    parser.add_argument("--country", default="country_code")
    parser.add_argument("--period", default="period")
    parser.add_argument("--replications", type=int, default=999)
    parser.add_argument("--confidence-level", type=float, default=0.95)
    parser.add_argument("--seed", type=int, default=2718)
    args = parser.parse_args()
    source = pd.read_csv(args.input)
    sample = common_dynamic_sample(
        source, outcome=args.outcome, lagged_outcome=args.lagged_outcome,
        covariates=args.covariate, city=args.city, country=args.country, period=args.period,
    )
    result = bootstrap_dynamic_hierarchy(
        sample, outcome=args.outcome, lagged_outcome=args.lagged_outcome,
        covariates=args.covariate, city=args.city, country=args.country, period=args.period,
        replications=args.replications, confidence_level=args.confidence_level, seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(args.output)


if __name__ == "__main__":
    main()
