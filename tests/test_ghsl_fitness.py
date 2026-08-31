import pandas as pd
import pytest

from urban_growth.ghsl_fitness import apply_ghsl_fixed_forecast_fitness
from urban_growth.io import SourceSchemaError


def fixed_row(**overrides):
    row = {
        "city_id": "G1",
        "country_code": "AAA",
        "period_start": 2000,
        "period_end": 2005,
        "recent_growth": 0.02,
        "future_growth": 0.015,
        "boundary_mode": "fixed",
        "boundary_product": "ucdb_fixed_2025_boundary",
        "boundary_reference_year": 2025,
        "boundary_temporally_fixed": True,
        "boundary_history_uses_future_reference": True,
        "cross_stream_reconciled": True,
    }
    row.update(overrides)
    return row


def test_ghsl_fixed_is_growth_eligible_but_not_headline_or_deployable() -> None:
    result = apply_ghsl_fixed_forecast_fitness(pd.DataFrame([fixed_row()]))
    assert result.loc[0, "growth_eligible"]
    assert not result.loc[0, "headline_eligible"]
    assert not result.loc[0, "deployable_at_origin"]
    assert result.loc[0, "boundary_information_leakage"]
    assert "future_boundary_reference" in result.loc[0, "headline_exclusion_reasons"]
    assert result.loc[0, "benchmark_interpretation"] == "retrospective_stable_footprint_sensitivity"


def test_ghsl_fixed_is_not_spatially_eligible_without_validated_network_geography() -> None:
    result = apply_ghsl_fixed_forecast_fitness(pd.DataFrame([fixed_row()]))
    assert not result.loc[0, "spatial_eligible"]
    reasons = result.loc[0, "spatial_exclusion_reasons"]
    assert "coordinates_not_validated" in reasons
    assert "network_geography_not_validated" in reasons


def test_ghsl_fixed_requires_cross_stream_reconciliation() -> None:
    with pytest.raises(SourceSchemaError, match="reconciliation"):
        apply_ghsl_fixed_forecast_fitness(
            pd.DataFrame([fixed_row(cross_stream_reconciled=False)])
        )


def test_ghsl_fixed_rejects_dynamic_boundaries() -> None:
    with pytest.raises(SourceSchemaError, match="fixed-boundary"):
        apply_ghsl_fixed_forecast_fitness(pd.DataFrame([fixed_row(boundary_mode="dynamic")]))
