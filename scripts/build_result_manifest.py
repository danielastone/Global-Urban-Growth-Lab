"""Build a provenance-bound expected-output manifest for generated CSV files."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_growth.result_manifest import write_result_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--code-commit", required=True)
    parser.add_argument("--generation-command", required=True)
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("results", nargs="+", type=Path)
    args = parser.parse_args()
    write_result_manifest(
        args.output,
        args.results,
        root=args.root,
        code_commit=args.code_commit,
        generation_command=args.generation_command,
    )
    print(args.output)


if __name__ == "__main__":
    main()
