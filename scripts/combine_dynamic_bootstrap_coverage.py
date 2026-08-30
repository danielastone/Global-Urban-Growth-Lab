"""Combine and validate the nine production coverage-cell artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_growth.dynamic_estimators import combine_coverage_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = combine_coverage_artifacts(args.input_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(args.output)


if __name__ == "__main__":
    main()
