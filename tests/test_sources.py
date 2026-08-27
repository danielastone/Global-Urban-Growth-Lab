import json

import pytest

from urban_growth.sources import (
    SourceCatalogError,
    inventory_file,
    load_catalog,
    source_by_id,
    validate_catalog,
)


def test_repository_catalog_is_valid() -> None:
    catalog = load_catalog("data/sources.json")
    assert len(catalog["sources"]) == 5
    ghsl = source_by_id(catalog, "ec_ghsl_ucdb_r2024a_v1_1")
    wup = source_by_id(catalog, "un_wup_2025_degurb")
    assert ghsl["independence_group"] == wup["independence_group"]


def test_duplicate_source_ids_fail() -> None:
    catalog = load_catalog("data/sources.json")
    catalog = json.loads(json.dumps(catalog))
    catalog["sources"].append(catalog["sources"][0])
    with pytest.raises(SourceCatalogError, match="Duplicate"):
        validate_catalog(catalog)


def test_inventory_hashes_exact_file(tmp_path) -> None:
    path = tmp_path / "source.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")
    source = source_by_id(load_catalog("data/sources.json"), "un_wup_2025_degurb")
    record = inventory_file(
        path, source, source_url="https://population.un.org/example.csv",
        retrieved_at="2026-08-27",
    )
    assert record.sha256 == "492d5ea496056f1a6a6592241032fab764c321596317930b4fa0e1e8bc3b7470"
