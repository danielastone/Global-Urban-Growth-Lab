"""Exact fixed-polygon built-form decomposition."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


def built_form_decomposition(intervals: pd.DataFrame) -> pd.DataFrame:
    """Split annualized log volume growth into surface and mean-height terms.

    Mean height is the accounting ratio volume/surface. Its interpretation is
    supplied by ``height_lineage``; the identity does not prove observed vertical
    change.
    """
    required = {
        "city_id", "period_start", "period_end",
        "built_up_surface_start_m2", "built_up_surface_end_m2",
        "built_up_volume_start_m3", "built_up_volume_end_m3", "height_lineage",
    }
    require_columns(intervals, required, source_name="built-form intervals")
    reject_duplicate_keys(
        intervals, ["city_id", "period_start", "period_end"], source_name="built-form intervals"
    )
    out = intervals.copy()
    duration = out["period_end"] - out["period_start"]
    if (duration <= 0).any():
        raise SourceSchemaError("Built-form intervals require period_end > period_start")
    measures = [
        "built_up_surface_start_m2", "built_up_surface_end_m2",
        "built_up_volume_start_m3", "built_up_volume_end_m3",
    ]
    numeric = out[measures].apply(pd.to_numeric, errors="coerce")
    if numeric.isna().any().any() or (numeric <= 0).any().any():
        raise SourceSchemaError("Built-form decomposition requires positive numeric measures")
    for column in measures:
        out[column] = numeric[column]
    out["mean_height_start_m"] = (
        out["built_up_volume_start_m3"] / out["built_up_surface_start_m2"]
    )
    out["mean_height_end_m"] = (
        out["built_up_volume_end_m3"] / out["built_up_surface_end_m2"]
    )
    out["volume_annualized_log_growth"] = np.log(
        out["built_up_volume_end_m3"] / out["built_up_volume_start_m3"]
    ) / duration
    out["horizontal_annualized_log_growth"] = np.log(
        out["built_up_surface_end_m2"] / out["built_up_surface_start_m2"]
    ) / duration
    out["vertical_annualized_log_growth"] = np.log(
        out["mean_height_end_m"] / out["mean_height_start_m"]
    ) / duration
    residual = out["volume_annualized_log_growth"] - (
        out["horizontal_annualized_log_growth"] + out["vertical_annualized_log_growth"]
    )
    if not np.allclose(residual, 0.0, atol=1e-12, rtol=0):
        raise SourceSchemaError("Built-form log decomposition identity failed")
    out["decomposition_identity_residual"] = residual
    nonzero = out["volume_annualized_log_growth"].abs().gt(1e-12)
    out["horizontal_share_of_volume_growth"] = np.nan
    out["vertical_share_of_volume_growth"] = np.nan
    out.loc[nonzero, "horizontal_share_of_volume_growth"] = (
        out.loc[nonzero, "horizontal_annualized_log_growth"]
        / out.loc[nonzero, "volume_annualized_log_growth"]
    )
    out.loc[nonzero, "vertical_share_of_volume_growth"] = (
        out.loc[nonzero, "vertical_annualized_log_growth"]
        / out.loc[nonzero, "volume_annualized_log_growth"]
    )
    out["share_defined"] = nonzero
    out["vertical_change_observed"] = ~out["height_lineage"].eq(
        "ghs_built_v_surface_epoch_scaled_by_2018_height"
    )
    return out.sort_values(["city_id", "period_start", "period_end"]).reset_index(drop=True)
