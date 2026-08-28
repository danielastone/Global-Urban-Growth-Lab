import csv

import pytest

from urban_growth.io import SourceSchemaError
from urban_growth.result_manifest import csv_dimensions, file_sha256, verify_result_manifest


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
