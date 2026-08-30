"""Run the preregistered finite-T dynamic-estimator simulation grid."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_growth.dynamic_estimators import simulate_dynamic_hierarchy


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/dynamic_estimator_simulation.csv")
    )
    parser.add_argument("--replications", type=int, default=25)
    parser.add_argument("--cities", type=int, default=48)
    parser.add_argument("--countries", type=int, default=6)
    parser.add_argument("--seed", type=int, default=1729)
    args = parser.parse_args()
    result = simulate_dynamic_hierarchy(
        replications=args.replications,
        cities=args.cities,
        countries=args.countries,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(args.output)


if __name__ == "__main__":
    main()
