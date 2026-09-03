"""Acquire and verify the registered 100 m GHS-POP tiles covering Japan DIDs."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from urllib.request import urlopen

from urban_growth.io import SourceSchemaError
from urban_growth.japan_did import ghsl_japan_tile_names, ghsl_japan_tile_url


def registered_hashes(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        rows[name.strip()] = digest
    if set(rows) != set(ghsl_japan_tile_names()):
        raise SourceSchemaError("Japan GHS-POP hash register does not match tile universe")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw/japan_ghsl_pop"))
    parser.add_argument(
        "--hash-register",
        type=Path,
        default=Path("results/japan_ghsl_pop_source_sha256.txt"),
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    expected = registered_hashes(args.hash_register)
    for name in ghsl_japan_tile_names():
        target = args.output_dir / name
        if not target.is_file():
            with urlopen(ghsl_japan_tile_url(name), timeout=180) as response:
                target.write_bytes(response.read())
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected[name]:
            raise SourceSchemaError(f"Japan GHS-POP source hash mismatch: {name}")
        print(f"{actual}  {name}")


if __name__ == "__main__":
    main()
