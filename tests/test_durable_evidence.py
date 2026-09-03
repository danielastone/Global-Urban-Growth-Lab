import csv
from pathlib import Path

import pytest

from urban_growth.durable_evidence import (
    OUTPUT_FIELDS,
    PACKAGE_FIELDS,
    validate_durable_evidence,
)
from urban_growth.io import SourceSchemaError
from urban_growth.result_manifest import file_sha256


def _write_csv(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _fixture(root: Path) -> tuple[Path, Path]:
    (root / "docs").mkdir()
    (root / ".github/workflows").mkdir(parents=True)
    (root / "results").mkdir()
    (root / "docs/result.md").write_text(
        "GitHub Actions run 123456\n", encoding="utf-8"
    )
    (root / ".github/workflows/run.yml").write_text("name: run\n", encoding="utf-8")
    (root / "results/input-hashes.txt").write_text(
        "a" * 64 + "  raw.csv\n", encoding="utf-8"
    )
    (root / "results/output.csv").write_text("x,y\n1,2\n", encoding="utf-8")
    package_path = root / "results/packages.csv"
    output_path = root / "results/outputs.csv"
    _write_csv(
        package_path,
        PACKAGE_FIELDS,
        [
            {
                "package_id": "package",
                "result_document": "docs/result.md",
                "workflow_path": ".github/workflows/run.yml",
                "workflow_run_id": "123456",
                "artifact_id": "654321",
                "artifact_name": "artifact",
                "artifact_sha256": "b" * 64,
                "artifact_expires_at": "2026-11-30T00:00:00Z",
                "producing_commit": "c" * 40,
                "generation_command": "python run.py",
                "parameters_json": "{}",
                "source_ids_json": '["source"]',
                "input_hash_manifest": "results/input-hashes.txt",
                "input_hash_manifest_sha256": file_sha256(
                    root / "results/input-hashes.txt"
                ),
                "storage_class": "git_repository",
                "retention_policy": "retained_with_git_history",
                "evidence_owner": "owner",
                "expected_availability": "public_while_repository_retained",
                "restoration_procedure": "checkout results/output.csv",
                "rights_scope": "synthetic",
                "notes": "fixture",
            }
        ],
    )
    _write_csv(
        output_path,
        OUTPUT_FIELDS,
        [
            {
                "package_id": "package",
                "artifact_member": "outputs/output.csv",
                "repository_path": "results/output.csv",
                "sha256": file_sha256(root / "results/output.csv"),
                "rows": "1",
                "columns": "2",
                "media_type": "text/csv",
                "storage_status": "committed",
            }
        ],
    )
    return package_path, output_path


def test_repository_durable_evidence_is_valid() -> None:
    validate_durable_evidence(
        Path("results/durable_evidence_packages.csv"),
        Path("results/durable_evidence_outputs.csv"),
    )


def test_durable_fixture_validates(tmp_path: Path) -> None:
    packages, outputs = _fixture(tmp_path)
    validate_durable_evidence(packages, outputs, root=tmp_path)


def test_changed_output_fails(tmp_path: Path) -> None:
    packages, outputs = _fixture(tmp_path)
    (tmp_path / "results/output.csv").write_text("x,y\n9,9\n", encoding="utf-8")
    with pytest.raises(SourceSchemaError, match="output checksum"):
        validate_durable_evidence(packages, outputs, root=tmp_path)


def test_unregistered_transient_reference_fails(tmp_path: Path) -> None:
    packages, outputs = _fixture(tmp_path)
    (tmp_path / "docs/unregistered.md").write_text(
        "artifact ID 777777\n", encoding="utf-8"
    )
    with pytest.raises(SourceSchemaError, match="lack durable packages"):
        validate_durable_evidence(packages, outputs, root=tmp_path)


def test_changed_input_manifest_fails(tmp_path: Path) -> None:
    packages, outputs = _fixture(tmp_path)
    (tmp_path / "results/input-hashes.txt").write_text(
        "d" * 64 + "  raw.csv\n", encoding="utf-8"
    )
    with pytest.raises(SourceSchemaError, match="input manifest digest"):
        validate_durable_evidence(packages, outputs, root=tmp_path)
