import pandas as pd
import pytest

from urban_growth.io import SourceSchemaError
from urban_growth.selection import (
    ghsl_forecast_selection_ledger,
    selection_summary,
    wup_forecast_selection_ledger,
)


def test_wup_ledger_exposes_threshold_and_future_projection_selection() -> None:
    rows = []
    for city_id, entry, eligible in [(1, 2015, True), (2, 2015, True), (3, 2030, False)]:
        for year in range(entry, 2036, 5):
            rows.append(
                {
                    "city_id": city_id,
                    "year": year,
                    "population": 50_000 + year,
                    "ISO3_Code": "AAA",
                    "City_Name": f"City {city_id}",
                    "sample_entry_year": entry,
                    "sample_exit_year": 2035,
                    "eligible_at_reference_year": eligible,
                    "observation_type": "estimate" if year <= 2025 else "projection",
                }
            )
    population = pd.DataFrame(rows)
    analytical = population.loc[population["city_id"].ne(2) | population["year"].ne(2020)]
    ledger = wup_forecast_selection_ledger(population, analytical, [2020])
    included = ledger.set_index("city_id")
    assert included.loc[1, "included"]
    assert included.loc[2, "primary_exclusion_reason"] == "origin_covariates_missing"
    assert included.loc[3, "primary_exclusion_reason"] == (
        "population_lag_missing_threshold_blank"
    )
    assert included.loc[3, "entry_occurs_in_projection_period"]
    assert included.loc[3, "not_eligible_at_2025_reference"]
    assert included.loc[3, "future_projection_selected"]


def test_ghsl_ledgers_keep_fixed_and_dynamic_semantics_explicit() -> None:
    fixed = pd.DataFrame(
        {
            "city_id": [1, 1, 1],
            "year": [2015, 2020, 2025],
            "boundary_mode": ["fixed"] * 3,
            "GC_CNT_GAD_2025": ["AAA"] * 3,
        }
    )
    fixed_ledger = ghsl_forecast_selection_ledger(fixed, [2020], boundary_mode="fixed")
    assert fixed_ledger.loc[0, "included"]
    assert fixed_ledger.loc[0, "uses_future_reference_polygon"]
    assert fixed_ledger.loc[0, "geographic_comparability"] == (
        "fixed_2025_polygon_using_future_reference"
    )

    dynamic = fixed.assign(
        boundary_mode="dynamic",
        quality_controlled_2025=False,
        **{"GC_UCB_YOB _2025": 2015, "GC_UCB_YOD _2025": 2025},
    )
    dynamic_ledger = ghsl_forecast_selection_ledger(
        dynamic, [2020], boundary_mode="dynamic"
    )
    assert not dynamic_ledger.loc[0, "included"]
    assert dynamic_ledger.loc[0, "conditioned_on_2025_quality"]
    assert dynamic_ledger.loc[0, "primary_exclusion_reason"] == (
        "not_quality_controlled_at_2025"
    )


def test_selection_summary_uses_full_origin_universe() -> None:
    ledger = pd.DataFrame(
        {
            "source_stream": ["x", "x"],
            "geographic_comparability": ["fixed", "fixed"],
            "origin": [2020, 2020],
            "country_code": ["A", "B"],
            "city_id": [1, 2],
            "included": [True, False],
            "primary_exclusion_reason": ["included", "missing"],
        }
    )
    summary = selection_summary(ledger)
    assert summary["origin_universe_rows"].eq(2).all()
    assert summary["share_of_origin_universe"].tolist() == pytest.approx([0.5, 0.5])


def test_selection_audit_rejects_duplicate_city_years() -> None:
    panel = pd.DataFrame(
        {
            "city_id": [1, 1],
            "year": [2020, 2020],
            "boundary_mode": ["fixed", "fixed"],
            "GC_CNT_GAD_2025": ["AAA", "AAA"],
        }
    )
    with pytest.raises(SourceSchemaError, match="duplicate"):
        ghsl_forecast_selection_ledger(panel, [2020], boundary_mode="fixed")
