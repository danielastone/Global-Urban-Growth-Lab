import pandas as pd
import pytest

from urban_growth.io import SourceSchemaError
from urban_growth.mexico_acquisition import (
    require_mexico_acquisition_ready,
    validate_mexico_acquisition_registry,
)


def _row(role, year, *, status="acquired"):
    return {
        "role": role,
        "event_year": year,
        "event_type": "census" if year not in {1995, 2005} else "population_count",
        "publisher": "INEGI",
        "dataset": f"test {role} {year}",
        "retrieved_at": "2026-08-31",
        "source_url": "https://www.inegi.org.mx/example",
        "local_path": f"data/raw/{role}_{year}.csv",
        "sha256": "a" * 64,
        "license_reviewed": True,
        "completeness_verified": True,
        "national_record_cap_avoided": True,
        "status": status,
    }


def _complete_registry():
    years = [1990, 1995, 2000, 2005, 2010, 2020]
    rows = [_row("population", year) for year in years]
    rows += [_row("vintage_geometry", year) for year in years]
    rows += [_row("official_relationships", 2020), _row("locality_history", 2020)]
    return pd.DataFrame(rows)


def test_complete_registry_is_ready():
    checked = require_mexico_acquisition_ready(_complete_registry())
    assert checked.attrs["mexico_acquisition_ready"] is True


def test_missing_population_wave_fails_closed():
    registry = _complete_registry()
    registry = registry.loc[~((registry["role"] == "population") & (registry["event_year"] == 1995))]
    checked = validate_mexico_acquisition_registry(registry)
    assert checked.attrs["missing_population_years"] == [1995]
    with pytest.raises(SourceSchemaError, match=r"population years=\[1995\]"):
        require_mexico_acquisition_ready(registry)


def test_national_record_cap_must_be_avoided():
    registry = _complete_registry()
    registry.loc[registry.index[0], "national_record_cap_avoided"] = False
    with pytest.raises(SourceSchemaError, match="national_record_cap_avoided"):
        validate_mexico_acquisition_registry(registry)


def test_landing_page_without_hash_is_not_acquired_input():
    registry = _complete_registry()
    registry.loc[registry.index[0], "sha256"] = ""
    with pytest.raises(SourceSchemaError, match="SHA-256"):
        validate_mexico_acquisition_registry(registry)


def test_missing_vintage_geometry_blocks_readiness():
    registry = _complete_registry()
    registry = registry.loc[
        ~((registry["role"] == "vintage_geometry") & (registry["event_year"] == 2005))
    ]
    with pytest.raises(SourceSchemaError, match=r"geometry years=\[2005\]"):
        require_mexico_acquisition_ready(registry)
