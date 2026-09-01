import pandas as pd
import pytest

from urban_growth.bootstrap_dependence import (
    block_two_way_cluster_bootstrap_paired_difference,
)
from urban_growth.io import SourceSchemaError


def _errors() -> pd.DataFrame:
    rows = []
    for origin in [2000, 2005, 2010, 2015]:
        for city_id, country, difference in [
            (1, "A", -0.01),
            (2, "B", 0.02),
            (3, "C", -0.02),
        ]:
            for model, error in [
                ("persistence", 0.05 + difference),
                ("country_mean_leave_city_out", 0.05),
            ]:
                rows.append(
                    {
                        "city_id": city_id,
                        "country_code": country,
                        "origin": origin,
                        "model": model,
                        "absolute_error": error,
                    }
                )
    return pd.DataFrame(rows)


def test_overlapping_origins_use_moving_blocks() -> None:
    first = block_two_way_cluster_bootstrap_paired_difference(
        _errors(), forecast_horizon_years=10, repetitions=200, seed=13
    )
    second = block_two_way_cluster_bootstrap_paired_difference(
        _errors(), forecast_horizon_years=10, repetitions=200, seed=13
    )
    pd.testing.assert_frame_equal(first, second)
    row = first.iloc[0]
    assert row["origins_overlap"]
    assert row["minimum_origin_spacing_years"] == pytest.approx(5.0)
    assert row["time_block_length"] == 2
    assert row["time_resampling_scheme"] == "circular_moving_origin_blocks"
    assert row["adjacent_origin_blocks_preserved"]
    assert row["country_cluster_preserves_nested_city_trajectories"]


def test_nonoverlapping_origins_need_no_time_blocking() -> None:
    result = block_two_way_cluster_bootstrap_paired_difference(
        _errors(), forecast_horizon_years=5, repetitions=200, seed=13
    )
    row = result.iloc[0]
    assert not row["origins_overlap"]
    assert row["time_block_length"] == 1
    assert row["time_resampling_scheme"] == "exchangeable_origin_clusters"
    assert not row["adjacent_origin_blocks_preserved"]


def test_block_bootstrap_requires_declared_positive_horizon() -> None:
    with pytest.raises(SourceSchemaError, match="Forecast horizon must be positive"):
        block_two_way_cluster_bootstrap_paired_difference(
            _errors(), forecast_horizon_years=0, repetitions=200
        )
