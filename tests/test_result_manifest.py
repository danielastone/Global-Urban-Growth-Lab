import csv
from pathlib import Path

import pytest

from urban_growth.io import SourceSchemaError
from urban_growth.result_manifest import (
    canonical_csv_sha256,
    csv_dimensions,
    file_sha256,
    verify_result_manifest,
    write_result_manifest,
)


def test_result_manifest_verifies_hash_and_dimensions(tmp_path) -> None:
    result = tmp_path / "result.csv"
    result.write_text("a,b\n1,2\n", encoding="utf-8")
    rows, columns = csv_dimensions(result)
    manifest = tmp_path / "manifest.csv"
    with manifest.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["path", "sha256", "rows", "columns"])
        writer.writeheader()
        writer.writerow(
            {
                "path": "result.csv", "sha256": file_sha256(result),
                "rows": rows, "columns": columns,
            }
        )
    verify_result_manifest(manifest, root=tmp_path)
    result.write_text("a,b\n1,3\n", encoding="utf-8")
    with pytest.raises(SourceSchemaError, match="checksum"):
        verify_result_manifest(manifest, root=tmp_path)


def test_provenance_manifest_verifies_artifact_and_inputs(tmp_path) -> None:
    (tmp_path / "data").mkdir()
    (tmp_path / "uv.lock").write_text("locked\n", encoding="utf-8")
    (tmp_path / "data" / "manifest.csv").write_text("source_id\nA\n", encoding="utf-8")
    result = tmp_path / "result.csv"
    result.write_text("a,b\n1,0.12345678901234\n", encoding="utf-8")
    manifest = tmp_path / "manifest.csv"
    write_result_manifest(
        manifest,
        [Path("result.csv")],
        root=tmp_path,
        code_commit="a" * 40,
        generation_command="python scripts/example.py",
    )
    verify_result_manifest(manifest, root=tmp_path)
    assert canonical_csv_sha256(result)

    (tmp_path / "uv.lock").write_text("changed\n", encoding="utf-8")
    with pytest.raises(SourceSchemaError, match="environment provenance"):
        verify_result_manifest(manifest, root=tmp_path)


def test_provenance_manifest_rejects_partial_metadata(tmp_path) -> None:
    result = tmp_path / "result.csv"
    result.write_text("a\n1\n", encoding="utf-8")
    manifest = tmp_path / "manifest.csv"
    manifest.write_text(
        "path,sha256,rows,columns,code_commit\n"
        f"result.csv,{file_sha256(result)},1,1,{'a' * 40}\n",
        encoding="utf-8",
    )
    with pytest.raises(SourceSchemaError, match="partial provenance"):
        verify_result_manifest(manifest, root=tmp_path)
