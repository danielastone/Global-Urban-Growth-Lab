"""Fail-closed provenance contracts for population-reliability evidence."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

from urban_growth.sources import SourceCatalogError, license_by_source_id, source_by_id

SNAPSHOT_FIELDS = [
    "snapshot_id",
    "source_id",
    "source_url",
    "retrieval_method",
    "retrieved_at",
    "source_release",
    "source_observation_start",
    "source_observation_end",
    "local_path",
    "sha256",
    "media_type",
    "license_id",
    "redistribution_status",
    "capture_notes",
]

TRANSFORMATION_FIELDS = [
    "transformation_run_id",
    "code_commit",
    "entry_point",
    "parameters_json",
    "input_snapshot_ids",
    "started_at",
    "completed_at",
    "output_path",
    "output_sha256",
]

RETRIEVAL_METHODS = {"file_download", "api_capture", "manual_evidence"}
SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")
COMMIT_PATTERN = re.compile(r"[0-9a-f]{40}")
YEAR_PATTERN = re.compile(r"[0-9]{4}")


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _validate_sha256(value: str, *, field: str) -> None:
    if not SHA256_PATTERN.fullmatch(value):
        raise SourceCatalogError(f"{field} must be a lowercase 64-character SHA-256")


def _validate_https(value: str, *, field: str) -> None:
    parsed = urlparse(value)
    if parsed.scheme != "https" or not parsed.netloc:
        raise SourceCatalogError(f"{field} must be an HTTPS URL")


def _validate_utc_timestamp(value: str, *, field: str) -> datetime:
    if not value.endswith("Z"):
        raise SourceCatalogError(f"{field} must be an ISO-8601 UTC timestamp ending in Z")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise SourceCatalogError(f"{field} is not a valid ISO-8601 timestamp") from error
    if parsed.tzinfo != UTC:
        raise SourceCatalogError(f"{field} must be UTC")
    return parsed


def _validate_relative_path(value: str, *, field: str) -> None:
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or value.strip() != value or not value:
        raise SourceCatalogError(f"{field} must be a normalized relative project path")


def _observation_bound(value: str, *, field: str, end: bool) -> tuple[int, int, int]:
    if YEAR_PATTERN.fullmatch(value):
        return (int(value), 12, 31) if end else (int(value), 1, 1)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise SourceCatalogError(f"{field} must be a year or ISO-8601 date") from error
    return parsed.year, parsed.month, parsed.day


def snapshot_id_for(source_id: str, sha256: str) -> str:
    """Return the immutable snapshot identity for captured bytes."""
    if not source_id or source_id.strip() != source_id:
        raise SourceCatalogError("source_id must be a non-empty normalized string")
    _validate_sha256(sha256, field="sha256")
    return f"{source_id}:{sha256}"


def transformation_run_id_for(
    *,
    code_commit: str,
    entry_point: str,
    parameters: Mapping[str, Any],
    input_snapshot_ids: Iterable[str],
    output_sha256: str,
) -> str:
    """Hash the immutable transformation recipe and output identity."""
    inputs = tuple(sorted(input_snapshot_ids))
    payload = {
        "code_commit": code_commit,
        "entry_point": entry_point,
        "parameters": dict(parameters),
        "input_snapshot_ids": inputs,
        "output_sha256": output_sha256,
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return f"transform:{digest}"


@dataclass(frozen=True)
class DatasetSnapshot:
    snapshot_id: str
    source_id: str
    source_url: str
    retrieval_method: str
    retrieved_at: str
    source_release: str
    source_observation_start: str
    source_observation_end: str
    local_path: str
    sha256: str
    media_type: str
    license_id: str
    redistribution_status: str
    capture_notes: str

    def as_dict(self) -> dict[str, str]:
        return {field: str(getattr(self, field)) for field in SNAPSHOT_FIELDS}


@dataclass(frozen=True)
class TransformationRun:
    transformation_run_id: str
    code_commit: str
    entry_point: str
    parameters_json: str
    input_snapshot_ids: str
    started_at: str
    completed_at: str
    output_path: str
    output_sha256: str

    @classmethod
    def build(
        cls,
        *,
        code_commit: str,
        entry_point: str,
        parameters: Mapping[str, Any],
        input_snapshot_ids: Iterable[str],
        started_at: str,
        completed_at: str,
        output_path: str,
        output_sha256: str,
    ) -> TransformationRun:
        inputs = tuple(sorted(input_snapshot_ids))
        return cls(
            transformation_run_id=transformation_run_id_for(
                code_commit=code_commit,
                entry_point=entry_point,
                parameters=parameters,
                input_snapshot_ids=inputs,
                output_sha256=output_sha256,
            ),
            code_commit=code_commit,
            entry_point=entry_point,
            parameters_json=_canonical_json(dict(parameters)),
            input_snapshot_ids=_canonical_json(inputs),
            started_at=started_at,
            completed_at=completed_at,
            output_path=output_path,
            output_sha256=output_sha256,
        )

    def as_dict(self) -> dict[str, str]:
        return {field: str(getattr(self, field)) for field in TRANSFORMATION_FIELDS}


def snapshot_from_manifest_record(
    record: Mapping[str, str],
    *,
    catalog: dict,
    licenses: dict,
    retrieval_method: str,
    retrieved_at: str,
    media_type: str,
    source_observation_start: str = "",
    source_observation_end: str = "",
    capture_notes: str = "",
) -> DatasetSnapshot:
    """Promote a legacy file-manifest row without inventing missing capture metadata."""
    required = {
        "source_id",
        "release",
        "source_url",
        "local_path",
        "sha256",
        "redistribution_allowed",
    }
    missing = sorted(required.difference(record))
    if missing:
        raise SourceCatalogError(f"Manifest record missing fields: {', '.join(missing)}")
    source = source_by_id(catalog, record["source_id"])
    license_record = license_by_source_id(licenses, record["source_id"])
    if record["release"] != source["release"]:
        raise SourceCatalogError("Manifest release does not match the registered source release")
    return DatasetSnapshot(
        snapshot_id=snapshot_id_for(record["source_id"], record["sha256"]),
        source_id=record["source_id"],
        source_url=record["source_url"],
        retrieval_method=retrieval_method,
        retrieved_at=retrieved_at,
        source_release=record["release"],
        source_observation_start=source_observation_start,
        source_observation_end=source_observation_end,
        local_path=record["local_path"],
        sha256=record["sha256"],
        media_type=media_type,
        license_id=license_record["license_id"],
        redistribution_status=record["redistribution_allowed"],
        capture_notes=capture_notes,
    )


def validate_dataset_snapshots(
    snapshots: Iterable[DatasetSnapshot], *, catalog: dict, licenses: dict
) -> None:
    """Validate immutable snapshots against the existing source and rights registries."""
    rows = list(snapshots)
    ids = [row.snapshot_id for row in rows]
    if len(ids) != len(set(ids)):
        raise SourceCatalogError("Duplicate snapshot_id values")
    for row in rows:
        source = source_by_id(catalog, row.source_id)
        license_record = license_by_source_id(licenses, row.source_id)
        if row.snapshot_id != snapshot_id_for(row.source_id, row.sha256):
            raise SourceCatalogError("snapshot_id does not match source_id and captured bytes")
        if row.source_release != source["release"]:
            raise SourceCatalogError(f"{row.snapshot_id} release is not registered in sources.json")
        if row.license_id != license_record["license_id"]:
            raise SourceCatalogError(f"{row.snapshot_id} license_id does not match licenses.json")
        _validate_https(row.source_url, field="source_url")
        if row.retrieval_method not in RETRIEVAL_METHODS:
            raise SourceCatalogError(f"{row.snapshot_id} has invalid retrieval_method")
        _validate_utc_timestamp(row.retrieved_at, field="retrieved_at")
        observation_start = _observation_bound(
            row.source_observation_start, field="source_observation_start", end=False
        )
        observation_end = _observation_bound(
            row.source_observation_end, field="source_observation_end", end=True
        )
        if observation_end < observation_start:
            raise SourceCatalogError("source_observation_end cannot precede start")
        _validate_relative_path(row.local_path, field="local_path")
        if not row.media_type or "/" not in row.media_type:
            raise SourceCatalogError(f"{row.snapshot_id} has invalid media_type")
        if not row.redistribution_status:
            raise SourceCatalogError(f"{row.snapshot_id} lacks redistribution_status")
        if row.retrieval_method == "manual_evidence" and not row.capture_notes.strip():
            raise SourceCatalogError("manual_evidence snapshots require capture_notes")


def validate_transformation_runs(
    runs: Iterable[TransformationRun], *, snapshots: Iterable[DatasetSnapshot]
) -> None:
    """Validate deterministic transformations and their snapshot foreign keys."""
    rows = list(runs)
    snapshot_ids = {row.snapshot_id for row in snapshots}
    run_ids = [row.transformation_run_id for row in rows]
    if len(run_ids) != len(set(run_ids)):
        raise SourceCatalogError("Duplicate transformation_run_id values")
    for row in rows:
        if not COMMIT_PATTERN.fullmatch(row.code_commit):
            raise SourceCatalogError("code_commit must be a full lowercase Git SHA")
        if not row.entry_point.strip():
            raise SourceCatalogError("entry_point must be non-empty")
        try:
            parameters = json.loads(row.parameters_json)
            input_ids = json.loads(row.input_snapshot_ids)
        except json.JSONDecodeError as error:
            raise SourceCatalogError("Transformation JSON fields must be valid JSON") from error
        if not isinstance(parameters, dict) or row.parameters_json != _canonical_json(parameters):
            raise SourceCatalogError("parameters_json must be a canonical JSON object")
        if (
            not isinstance(input_ids, list)
            or not input_ids
            or input_ids != sorted(set(input_ids))
            or row.input_snapshot_ids != _canonical_json(input_ids)
        ):
            raise SourceCatalogError("input_snapshot_ids must be canonical, unique, and sorted")
        unknown = sorted(set(input_ids).difference(snapshot_ids))
        if unknown:
            raise SourceCatalogError(f"Unknown input snapshot IDs: {', '.join(unknown)}")
        started = _validate_utc_timestamp(row.started_at, field="started_at")
        completed = _validate_utc_timestamp(row.completed_at, field="completed_at")
        if completed < started:
            raise SourceCatalogError("completed_at cannot precede started_at")
        _validate_relative_path(row.output_path, field="output_path")
        _validate_sha256(row.output_sha256, field="output_sha256")
        expected = transformation_run_id_for(
            code_commit=row.code_commit,
            entry_point=row.entry_point,
            parameters=parameters,
            input_snapshot_ids=input_ids,
            output_sha256=row.output_sha256,
        )
        if row.transformation_run_id != expected:
            raise SourceCatalogError("transformation_run_id does not match immutable lineage")


def validate_evidence_lineage(
    records: Iterable[Mapping[str, Any]],
    *,
    snapshots: Iterable[DatasetSnapshot],
    runs: Iterable[TransformationRun],
) -> None:
    """Reject evidence rows that cannot reach a captured input and transformation."""
    snapshot_by_id = {row.snapshot_id: row for row in snapshots}
    run_by_id = {row.transformation_run_id: row for row in runs}
    for index, record in enumerate(records):
        snapshot_id = record.get("snapshot_id")
        run_id = record.get("transformation_run_id")
        if not snapshot_id or snapshot_id not in snapshot_by_id:
            raise SourceCatalogError(f"Evidence row {index} has no registered snapshot")
        if not run_id or run_id not in run_by_id:
            raise SourceCatalogError(f"Evidence row {index} has no registered transformation")
        input_ids = set(json.loads(run_by_id[run_id].input_snapshot_ids))
        if snapshot_id not in input_ids:
            raise SourceCatalogError(
                f"Evidence row {index} snapshot is not an input to its transformation"
            )
        snapshot = snapshot_by_id[snapshot_id]
        if record.get("source_id", snapshot.source_id) != snapshot.source_id:
            raise SourceCatalogError(f"Evidence row {index} source_id conflicts with snapshot")
        if record.get("source_release", snapshot.source_release) != snapshot.source_release:
            raise SourceCatalogError(f"Evidence row {index} release conflicts with snapshot")


def _load_csv_records(path: str | Path, fields: list[str]) -> list[dict[str, str]]:
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields:
            raise SourceCatalogError(f"{Path(path).name} header does not match required schema")
        return list(reader)


def load_dataset_snapshots(path: str | Path) -> list[DatasetSnapshot]:
    return [DatasetSnapshot(**row) for row in _load_csv_records(path, SNAPSHOT_FIELDS)]


def load_transformation_runs(path: str | Path) -> list[TransformationRun]:
    return [TransformationRun(**row) for row in _load_csv_records(path, TRANSFORMATION_FIELDS)]
