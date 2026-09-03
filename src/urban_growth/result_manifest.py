"""Verification helpers for deterministic generated research outputs."""

from __future__ import annotations

import csv
import gzip
import hashlib
import re
from pathlib import Path

import pandas as pd

from urban_growth.io import SourceSchemaError

REQUIRED_MANIFEST_COLUMNS = {"path", "sha256", "rows", "columns"}
PROVENANCE_MANIFEST_COLUMNS = {
    "canonical_sha256",
    "code_commit",
    "environment_lock_sha256",
    "source_manifest_sha256",
    "generation_command",
}
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def file_sha256(path: Path) -> str:
    """Return the SHA-256 digest for a file without loading it all into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def csv_dimensions(path: Path) -> tuple[int, int]:
    """Return data-row and header-column counts for a generated CSV."""
    with (
        gzip.open(path, mode="rt", newline="", encoding="utf-8")
        if path.suffix == ".gz"
        else path.open(newline="", encoding="utf-8")
    ) as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration as error:
            raise SourceSchemaError(f"Generated result is empty: {path}") from error
        rows = sum(1 for _ in reader)
    return rows, len(header)


def canonical_csv_sha256(path: Path, *, decimal_places: int = 12) -> str:
    """Hash a stable numeric representation in addition to the exact file bytes."""
    frame = pd.read_csv(path)
    float_columns = frame.select_dtypes(include="floating").columns
    frame[float_columns] = frame[float_columns].round(decimal_places)
    payload = frame.to_csv(
        index=False,
        lineterminator="\n",
        float_format=f"%.{decimal_places}g",
        na_rep="",
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def write_result_manifest(
    manifest_path: Path,
    result_paths: list[Path],
    *,
    root: Path = Path("."),
    code_commit: str,
    generation_command: str,
) -> None:
    """Write a provenance-bound manifest for generated CSV artifacts."""
    if not COMMIT_PATTERN.fullmatch(code_commit):
        raise SourceSchemaError("Result manifest code_commit must be a full Git SHA")
    if not generation_command.strip():
        raise SourceSchemaError("Result manifest generation_command is required")
    if not result_paths:
        raise SourceSchemaError("Result manifest requires at least one output")
    lock_path = root / "uv.lock"
    source_manifest_path = root / "data" / "manifest.csv"
    if not lock_path.is_file() or not source_manifest_path.is_file():
        raise SourceSchemaError("Result provenance requires uv.lock and data/manifest.csv")
    provenance = {
        "code_commit": code_commit,
        "environment_lock_sha256": file_sha256(lock_path),
        "source_manifest_sha256": file_sha256(source_manifest_path),
        "generation_command": generation_command.strip(),
    }
    fieldnames = [
        "path",
        "sha256",
        "canonical_sha256",
        "rows",
        "columns",
        "code_commit",
        "environment_lock_sha256",
        "source_manifest_sha256",
        "generation_command",
    ]
    rows: list[dict[str, str | int]] = []
    for relative_path in sorted(result_paths, key=str):
        path = root / relative_path
        if not path.is_file():
            raise SourceSchemaError(f"Generated result is missing: {relative_path}")
        row_count, column_count = csv_dimensions(path)
        rows.append(
            {
                "path": relative_path.as_posix(),
                "sha256": file_sha256(path),
                "canonical_sha256": canonical_csv_sha256(path),
                "rows": row_count,
                "columns": column_count,
                **provenance,
            }
        )
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


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
        columns = set(reader.fieldnames or [])
    if not entries:
        raise SourceSchemaError("Result manifest has no entries")
    provenance_columns = PROVENANCE_MANIFEST_COLUMNS.intersection(columns)
    if provenance_columns and provenance_columns != PROVENANCE_MANIFEST_COLUMNS:
        missing = PROVENANCE_MANIFEST_COLUMNS.difference(columns)
        raise SourceSchemaError(
            f"Result manifest has partial provenance: {', '.join(sorted(missing))}"
        )
    failures: list[str] = []
    if provenance_columns:
        expected_lock = file_sha256(root / "uv.lock")
        expected_sources = file_sha256(root / "data" / "manifest.csv")
        for entry in entries:
            if not COMMIT_PATTERN.fullmatch(entry["code_commit"]):
                failures.append(f"code commit {entry['path']}")
            if not entry["generation_command"].strip():
                failures.append(f"generation command {entry['path']}")
            if entry["environment_lock_sha256"] != expected_lock:
                failures.append(f"environment provenance {entry['path']}")
            if entry["source_manifest_sha256"] != expected_sources:
                failures.append(f"source provenance {entry['path']}")
    for entry in entries:
        path = root / entry["path"]
        if not path.is_file():
            failures.append(f"missing {entry['path']}")
            continue
        rows, columns = csv_dimensions(path)
        if file_sha256(path) != entry["sha256"]:
            failures.append(f"checksum {entry['path']}")
        if provenance_columns and canonical_csv_sha256(path) != entry["canonical_sha256"]:
            failures.append(f"canonical checksum {entry['path']}")
        if rows != int(entry["rows"]) or columns != int(entry["columns"]):
            failures.append(f"dimensions {entry['path']}")
    if failures:
        raise SourceSchemaError("Result verification failed: " + "; ".join(failures))
