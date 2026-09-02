"""Build the registered fixed-polygon/F01/F21 accounting reconciliation."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from urban_growth.national_envelope import extent_density_reconciliation


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed-polygon-intervals", required=True, type=Path)
    parser.add_argument("--national-intervals", required=True, type=Path)
    parser.add_argument("--constant-membership-intervals", required=True, type=Path)
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/extent_density_reconciliation.csv")
    )
    parser.add_argument("--relative-tolerance", type=float, default=1e-6)
    parser.add_argument("--absolute-tolerance", type=float, default=1.0)
    args = parser.parse_args()
    result = extent_density_reconciliation(
        pd.read_csv(args.fixed_polygon_intervals),
        pd.read_csv(args.national_intervals),
        pd.read_csv(args.constant_membership_intervals),
        relative_tolerance=args.relative_tolerance,
        absolute_tolerance=args.absolute_tolerance,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(args.output)


if __name__ == "__main__":
    main()
