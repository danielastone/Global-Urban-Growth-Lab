import json

import pytest

from urban_growth.sources import (
    SourceCatalogError,
    inventory_file,
    load_catalog,
    load_licenses,
    require_permitted_use,
    source_by_id,
    validate_catalog,
    validate_licenses,
)


def test_repository_catalog_is_valid() -> None:
    catalog = load_catalog("data/sources.json")
    assert len(catalog["sources"]) == 12
    ghsl = source_by_id(catalog, "ec_ghsl_ucdb_r2024a_v1_2")
    wup = source_by_id(catalog, "un_wup_2025_cities")
    assert "ec_ghsl_degurb_r2023a" in ghsl["upstream_dependencies"]
    assert "ec_ghsl_degurb_r2023a" in wup["upstream_dependencies"]
    accessibility = source_by_id(catalog, "map_accessibility_2015")
    assert accessibility["release"] == "2015 nominal year"
    assert accessibility["status"] == "modern_validation"
    census_dates = source_by_id(catalog, "unsd_census_dates_2026_02_03")
    assert census_dates["release"] == "Last updated 03 February 2026"
    assert "not evidence of results status" in census_dates["role"]


def test_duplicate_source_ids_fail() -> None:
    catalog = load_catalog("data/sources.json")
    catalog = json.loads(json.dumps(catalog))
    catalog["sources"].append(catalog["sources"][0])
    with pytest.raises(SourceCatalogError, match="Duplicate"):
        validate_catalog(catalog)


def test_dangling_dependency_fails() -> None:
    catalog = load_catalog("data/sources.json")
    catalog = json.loads(json.dumps(catalog))
    catalog["sources"][0]["upstream_dependencies"] = ["missing_source"]
    with pytest.raises(SourceCatalogError, match="Unknown upstream"):
        validate_catalog(catalog)


def test_inventory_hashes_exact_file(tmp_path) -> None:
    path = tmp_path / "source.csv"
    path.write_text("a,b\n1,2\n", encoding="utf-8")
    source = source_by_id(load_catalog("data/sources.json"), "un_wup_2025_cities")
    record = inventory_file(
        path,
        source,
        source_url="https://population.un.org/example.csv",
        retrieved_at="2026-08-27",
    )
    assert record.sha256 == "492d5ea496056f1a6a6592241032fab764c321596317930b4fa0e1e8bc3b7470"


def test_repository_license_registry_is_complete_and_fail_closed() -> None:
    catalog = load_catalog("data/sources.json")
    registry = load_licenses("data/licenses.json", catalog=catalog)
    assert registry["default_policy"] == "deny"
    assert len(registry["sources"]) == len(catalog["sources"])


def test_permitted_ghsl_commercial_ingestion_passes() -> None:
    registry = load_licenses("data/licenses.json")
    record = require_permitted_use(registry, "ec_ghsl_ucdb_r2024a_v1_2", "internal_commercial_use")
    assert record["license_id"] == "CC-BY-4.0"


@pytest.mark.parametrize(
    ("source_id", "decision"),
    [
        ("un_wup_2025_cities", "legal_review_required"),
        ("map_accessibility_2015", "unresolved"),
    ],
)
def test_non_permitted_commercial_ingestion_fails(source_id: str, decision: str) -> None:
    registry = load_licenses("data/licenses.json")
    with pytest.raises(SourceCatalogError, match=decision):
        require_permitted_use(registry, source_id, "internal_commercial_use")


def test_license_registry_must_match_catalog() -> None:
    catalog = load_catalog("data/sources.json")
    registry = load_licenses("data/licenses.json")
    registry = json.loads(json.dumps(registry))
    registry["sources"].pop()
    with pytest.raises(SourceCatalogError, match="mismatch"):
        validate_licenses(registry, catalog=catalog)


def test_unknown_license_use_fails() -> None:
    registry = load_licenses("data/licenses.json")
    with pytest.raises(SourceCatalogError, match="Unknown licensed use"):
        require_permitted_use(registry, "un_wup_2025_cities", "generic_commercial_use")
