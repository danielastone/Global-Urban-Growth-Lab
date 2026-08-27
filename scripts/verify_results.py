"""Verify generated result files against committed expected-output manifests."""

from __future__ import annotations

import argparse
from pathlib import Path

from urban_growth.result_manifest import verify_result_manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifests", nargs="+", type=Path)
    parser.add_argument("--root", type=Path, default=Path("."))
    args = parser.parse_args()
    for manifest in args.manifests:
        verify_result_manifest(manifest, root=args.root)
        print(f"verified: {manifest}")


if __name__ == "__main__":
    main()
