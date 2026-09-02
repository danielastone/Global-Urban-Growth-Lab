import pandas as pd
import pytest

from urban_growth.built_form import built_form_decomposition
from urban_growth.io import SourceSchemaError


def test_built_form_decomposition_is_exact() -> None:
    frame = pd.DataFrame({
        "city_id": ["A"], "period_start": [2016], "period_end": [2023],
        "built_up_surface_start_m2": [100.0], "built_up_surface_end_m2": [200.0],
        "built_up_volume_start_m3": [500.0], "built_up_volume_end_m3": [1200.0],
        "height_lineage": ["google_open_buildings_temporal_v1_independent_height"],
    })
    result = built_form_decomposition(frame).iloc[0]
    assert result["mean_height_start_m"] == 5
    assert result["mean_height_end_m"] == 6
    assert result["volume_annualized_log_growth"] == pytest.approx(
        result["horizontal_annualized_log_growth"] + result["vertical_annualized_log_growth"]
    )
    assert result["horizontal_share_of_volume_growth"] + result[
        "vertical_share_of_volume_growth"
    ] == pytest.approx(1)
    assert result["vertical_change_observed"]


def test_ghsl_fixed_height_is_not_labeled_observed_vertical_change() -> None:
    frame = pd.DataFrame({
        "city_id": ["A"], "period_start": [1975], "period_end": [1980],
        "built_up_surface_start_m2": [100.0], "built_up_surface_end_m2": [120.0],
        "built_up_volume_start_m3": [500.0], "built_up_volume_end_m3": [660.0],
        "height_lineage": ["ghs_built_v_surface_epoch_scaled_by_2018_height"],
    })
    result = built_form_decomposition(frame).iloc[0]
    assert result["vertical_annualized_log_growth"] != 0
    assert not result["vertical_change_observed"]


def test_built_form_decomposition_fails_closed() -> None:
    frame = pd.DataFrame({
        "city_id": ["A"], "period_start": [2023], "period_end": [2016],
        "built_up_surface_start_m2": [100.0], "built_up_surface_end_m2": [0.0],
        "built_up_volume_start_m3": [500.0], "built_up_volume_end_m3": [600.0],
        "height_lineage": ["independent"],
    })
    with pytest.raises(SourceSchemaError):
        built_form_decomposition(frame)
