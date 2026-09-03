"""Validate durable evidence packages for cited empirical results."""

from __future__ import annotations

import csv
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path, PurePosixPath

from urban_growth.io import SourceSchemaError
from urban_growth.result_manifest import csv_dimensions, file_sha256

PACKAGE_FIELDS = [
    "package_id",
    "result_document",
    "workflow_path",
    "workflow_run_id",
    "artifact_id",
    "artifact_name",
    "artifact_sha256",
    "artifact_expires_at",
    "producing_commit",
    "generation_command",
    "parameters_json",
    "source_ids_json",
    "input_hash_manifest",
    "input_hash_manifest_sha256",
    "storage_class",
    "retention_policy",
    "evidence_owner",
    "expected_availability",
    "restoration_procedure",
    "rights_scope",
    "notes",
]
OUTPUT_FIELDS = [
    "package_id",
    "artifact_member",
    "repository_path",
    "sha256",
    "rows",
    "columns",
    "media_type",
    "storage_status",
]
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")
HASH_LINE_PATTERN = re.compile(r"^[0-9a-f]{64}  \S+")
EXPIRING_REFERENCE_PATTERN = re.compile(
    r"(?:artifact ID|GitHub Actions run|successful run)[^\n]*?\d{6,}",
    re.IGNORECASE,
)


def _records(path: Path, fields: list[str]) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields:
            raise SourceSchemaError(f"{path.name} header does not match the durable contract")
        rows = list(reader)
    if not rows:
        raise SourceSchemaError(f"{path.name} has no records")
    return rows


def _relative_path(value: str, *, field: str) -> Path:
    pure = PurePosixPath(value)
    if not value or pure.is_absolute() or ".." in pure.parts:
        raise SourceSchemaError(f"{field} must be a relative repository path")
    return Path(*pure.parts)


def _unique(rows: list[dict[str, str]], field: str) -> None:
    duplicates = sorted(
        key for key, count in Counter(row[field] for row in rows).items() if count > 1
    )
    if duplicates:
        raise SourceSchemaError(f"Duplicate {field}: {', '.join(duplicates)}")


def validate_durable_evidence(
    package_path: Path,
    output_path: Path,
    *,
    root: Path = Path("."),
) -> None:
    """Fail unless every cited transient artifact has durable, hash-bound outputs."""
    packages = _records(package_path, PACKAGE_FIELDS)
    outputs = _records(output_path, OUTPUT_FIELDS)
    _unique(packages, "package_id")
    _unique(packages, "result_document")
    _unique(outputs, "repository_path")
    package_ids = {row["package_id"] for row in packages}
    failures: list[str] = []

    for package in packages:
        package_id = package["package_id"]
        for field in ("result_document", "workflow_path", "input_hash_manifest"):
            relative = _relative_path(package[field], field=field)
            if not (root / relative).is_file():
                failures.append(f"missing {field} for {package_id}")
        if not package["workflow_run_id"].isdigit() or not package["artifact_id"].isdigit():
            failures.append(f"invalid GitHub identifiers for {package_id}")
        if not SHA256_PATTERN.fullmatch(package["artifact_sha256"]):
            failures.append(f"invalid artifact digest for {package_id}")
        if not COMMIT_PATTERN.fullmatch(package["producing_commit"]):
            failures.append(f"invalid producing commit for {package_id}")
        try:
            expiry = datetime.fromisoformat(package["artifact_expires_at"])
            if expiry.tzinfo is None:
                raise ValueError
        except ValueError:
            failures.append(f"invalid artifact expiry for {package_id}")
        try:
            parameters = json.loads(package["parameters_json"])
            source_ids = json.loads(package["source_ids_json"])
        except json.JSONDecodeError:
            failures.append(f"invalid JSON metadata for {package_id}")
        else:
            if (
                not isinstance(parameters, dict)
                or not isinstance(source_ids, list)
                or not source_ids
            ):
                failures.append(f"invalid parameter or source metadata for {package_id}")
        manifest = root / _relative_path(
            package["input_hash_manifest"], field="input_hash_manifest"
        )
        if manifest.is_file():
            if file_sha256(manifest) != package["input_hash_manifest_sha256"]:
                failures.append(f"input manifest digest for {package_id}")
            if not any(
                HASH_LINE_PATTERN.match(line)
                for line in manifest.read_text(encoding="utf-8").splitlines()
            ):
                failures.append(f"input manifest has no file hashes for {package_id}")
        if package["storage_class"] != "git_repository":
            failures.append(f"unsupported storage class for {package_id}")
        if package["retention_policy"] != "retained_with_git_history":
            failures.append(f"non-durable retention policy for {package_id}")
        if (
            not package["evidence_owner"].strip()
            or not package["expected_availability"].strip()
            or package["expected_availability"] == "actions_artifact"
            or not package["generation_command"].strip()
            or not package["restoration_procedure"].strip()
        ):
            failures.append(f"missing retention or recovery metadata for {package_id}")
        if "http" in package["restoration_procedure"].lower():
            failures.append(f"restoration procedure contains a transient URL for {package_id}")

    output_count = Counter(row["package_id"] for row in outputs)
    for package_id in package_ids:
        if not output_count[package_id]:
            failures.append(f"package has no durable outputs: {package_id}")
    for output in outputs:
        package_id = output["package_id"]
        if package_id not in package_ids:
            failures.append(f"unknown package for {output['repository_path']}")
        if output["storage_status"] != "committed":
            failures.append(f"output is not committed: {output['repository_path']}")
        relative = _relative_path(output["repository_path"], field="repository_path")
        path = root / relative
        if not path.is_file():
            failures.append(f"missing output {output['repository_path']}")
            continue
        if output["media_type"] not in {
            "text/csv",
            "application/gzip",
        } or not SHA256_PATTERN.fullmatch(output["sha256"]):
            failures.append(f"invalid output metadata {output['repository_path']}")
            continue
        try:
            expected_rows = int(output["rows"])
            expected_columns = int(output["columns"])
        except ValueError:
            failures.append(f"invalid output dimensions {output['repository_path']}")
            continue
        rows, columns = csv_dimensions(path)
        if file_sha256(path) != output["sha256"]:
            failures.append(f"output checksum {output['repository_path']}")
        if rows != expected_rows or columns != expected_columns:
            failures.append(f"output dimensions {output['repository_path']}")

    registered_documents = {row["result_document"] for row in packages}
    cited_documents = {
        path.relative_to(root).as_posix()
        for path in (root / "docs").glob("*.md")
        if EXPIRING_REFERENCE_PATTERN.search(path.read_text(encoding="utf-8"))
    }
    missing_packages = sorted(cited_documents.difference(registered_documents))
    if missing_packages:
        failures.append(
            "transient artifact references lack durable packages: " + ", ".join(missing_packages)
        )
    if failures:
        raise SourceSchemaError("Durable evidence validation failed: " + "; ".join(failures))
