"""Verification helpers for deterministic generated research outputs."""

from __future__ import annotations

import csv
import hashlib
from pathlib import Path

from urban_growth.io import SourceSchemaError

REQUIRED_MANIFEST_COLUMNS = {"path", "sha256", "rows", "columns"}


def file_sha256(path: Path) -> str:
    """Return the SHA-256 digest for a file without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_dimensions(path: Path) -> tuple[int, int]:
    """Return data-row and header-column counts for a generated CSV."""
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as error:
            raise SourceSchemaError(f"Generated result is empty: {path}") from error
        rows = sum(1 for _ in reader)
    return rows, len(header)


def verify_result_manifest(manifest_path: Path, *, root: Path = Path(".")) -> None:
    """Fail when a generated CSV differs from its committed expected manifest."""
    with manifest_path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        missing = REQUIRED_MANIFEST_COLUMNS.difference(reader.fieldnames or [])
        if missing:
            raise SourceSchemaError(
                f"Result manifest missing columns: {', '.join(sorted(missing))}"
            )
        entries = list(reader)
    if not entries:
        raise SourceSchemaError("Result manifest has no entries")
    failures: list[str] = []
    for entry in entries:
        path = root / entry["path"]
        if not path.is_file():
            failures.append(f"missing {entry['path']}")
            continue
        rows, columns = csv_dimensions(path)
        if file_sha256(path) != entry["sha256"]:
            failures.append(f"checksum {entry['path']}")
        if rows != int(entry["rows"]) or columns != int(entry["columns"]):
            failures.append(f"dimensions {entry['path']}")
    if failures:
        raise SourceSchemaError("Result verification failed: " + "; ".join(failures))
