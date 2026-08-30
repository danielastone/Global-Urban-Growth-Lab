import json

import pandas as pd
import pytest

from urban_growth.adapters.us_census import (
    build_us_place_boundary_cohort,
    read_place_population_snapshot,
)
from urban_growth.io import SourceSchemaError


def test_read_place_population_snapshot_builds_geoid(tmp_path) -> None:
    path = tmp_path / "places.json"
    path.write_text(
        json.dumps([["NAME", "P001001", "state", "place"], ["Test city", "40000", "1", "123"]]),
        encoding="utf-8",
    )
    result = read_place_population_snapshot(path, year=2010)
    assert result.loc[0, "geoid"] == "0100123"
    assert result.loc[0, "population"] == 40_000


def test_us_place_cohort_requires_one_to_one_near_identical_land() -> None:
    population_2010 = pd.DataFrame(
        {
            "geoid": ["0100001", "0100002", "0100003"],
            "place_name": ["A", "B", "C"],
            "population": [40_000, 60_000, 30_000],
        }
    )
    population_2020 = pd.DataFrame(
        {
            "geoid": ["0100001", "0100002", "0100004"],
            "place_name": ["A", "B", "C successor"],
            "population": [55_000, 70_000, 45_000],
        }
    )
    relationship = pd.DataFrame(
        {
            "GEOID_PLACE_10": ["0100001", "0100002", "0100003"],
            "GEOID_PLACE_20": ["0100001", "0100002", "0100004"],
            "AREALAND_PLACE_10": [100, 100, 100],
            "AREALAND_PLACE_20": [100, 150, 100],
            "AREALAND_PART": [100, 100, 100],
        }
    )
    result = build_us_place_boundary_cohort(population_2010, population_2020, relationship)
    assert result["settlement_id"].tolist() == ["US_PLACE_2010_0100001", "US_PLACE_2010_0100003"]
    assert result["crossed_50000"].tolist() == [True, False]
    assert result["geography_status"].tolist() == ["stable", "official_crosswalk"]


def test_us_place_cohort_rejects_invalid_overlap_threshold() -> None:
    with pytest.raises(SourceSchemaError, match="land overlap"):
        build_us_place_boundary_cohort(
            pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), minimum_land_overlap=0
        )


def test_us_place_cohort_rejects_nonpositive_endpoint_population() -> None:
    population_2010 = pd.DataFrame(
        {"geoid": ["0100001"], "place_name": ["A"], "population": [40_000]}
    )
    population_2020 = pd.DataFrame({"geoid": ["0100001"], "place_name": ["A"], "population": [0]})
    relationship = pd.DataFrame(
        {
            "GEOID_PLACE_10": ["0100001"],
            "GEOID_PLACE_20": ["0100001"],
            "AREALAND_PLACE_10": [100],
            "AREALAND_PLACE_20": [100],
            "AREALAND_PART": [100],
        }
    )
    with pytest.raises(SourceSchemaError, match="positive and complete"):
        build_us_place_boundary_cohort(population_2010, population_2020, relationship)
