"""Fail when any eligible corrected-estimator coverage cell misses its locked gate."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from urban_growth.dynamic_estimators import check_coverage_gate


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("result", type=Path)
    args = parser.parse_args()
    result = pd.read_csv(args.result)
    check_coverage_gate(result)
    print("bootstrap coverage gate passed: 9/9 corrected-estimator cells")


if __name__ == "__main__":
    main()
