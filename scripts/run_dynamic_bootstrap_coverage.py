"""Run the predeclared finite-sample coverage gate for dynamic estimators."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_growth.dynamic_estimators import simulate_bootstrap_coverage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=Path("outputs/dynamic_bootstrap_coverage.csv")
    )
    parser.add_argument("--simulation-replications", type=int, default=200)
    parser.add_argument("--bootstrap-replications", type=int, default=399)
    parser.add_argument("--cities", type=int, default=48)
    parser.add_argument("--countries", type=int, default=6)
    parser.add_argument("--seed", type=int, default=314159)
    parser.add_argument(
        "--persistence", action="append", type=float,
        help="Repeat to run selected persistence cells; default: 0.2, 0.6, 0.9",
    )
    parser.add_argument(
        "--panel-length", action="append", type=int,
        help="Repeat to run selected panel-length cells; default: 6, 8, 10",
    )
    args = parser.parse_args()
    result = simulate_bootstrap_coverage(
        simulation_replications=args.simulation_replications,
        bootstrap_replications=args.bootstrap_replications,
        cities=args.cities,
        countries=args.countries,
        seed=args.seed,
        persistence_values=tuple(args.persistence or (0.2, 0.6, 0.9)),
        panel_lengths=tuple(args.panel_length or (6, 8, 10)),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(args.output, index=False)
    print(args.output)


if __name__ == "__main__":
    main()
