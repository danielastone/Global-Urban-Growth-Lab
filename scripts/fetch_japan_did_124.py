"""Acquire and verify the registered official MLIT A16 DID archives."""

from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
from urllib.request import urlopen

from urban_growth.io import SourceSchemaError
from urban_growth.japan_did import official_archive_names, official_archive_url


def registered_hashes(path: Path) -> dict[str, str]:
    rows: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        rows[name.strip()] = digest
    if set(rows) != set(official_archive_names()):
        raise SourceSchemaError("Japan DID hash register does not match archive universe")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw/japan_did"))
    parser.add_argument(
        "--hash-register", type=Path, default=Path("results/japan_did_source_sha256.txt")
    )
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    expected = registered_hashes(args.hash_register)
    for name in official_archive_names():
        target = args.output_dir / name
        if not target.is_file():
            with urlopen(official_archive_url(name), timeout=120) as response:
                target.write_bytes(response.read())
        actual = hashlib.sha256(target.read_bytes()).hexdigest()
        if actual != expected[name]:
            raise SourceSchemaError(f"Japan DID source hash mismatch: {name}")
        print(f"{actual}  {name}")


if __name__ == "__main__":
    main()
