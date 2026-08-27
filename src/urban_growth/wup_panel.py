"""Assembly of an internally consistent WUP city-year analytical panel."""

from __future__ import annotations

import pandas as pd

from urban_growth.adapters.wup import validate_density_identity
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


def _metric_subset(frame: pd.DataFrame, value_columns: list[str], *, source_name: str) -> pd.DataFrame:
    required = {"city_id", "year", *value_columns}
    require_columns(frame, required, source_name=source_name)
    reject_duplicate_keys(frame, ["city_id", "year"], source_name=source_name)
    return frame[["city_id", "year", *value_columns]].copy()


def build_wup_city_year_panel(
    population_panel: pd.DataFrame,
    area_panel: pd.DataFrame,
    built_per_capita_panel: pd.DataFrame,
    density_panel: pd.DataFrame,
) -> pd.DataFrame:
    """Join verified WUP metrics and derive built-up area with quality flags."""
    population_required = {
        "city_id", "year", "population", "observation_type", "ISO3_Code", "City_Name",
        "PWCent_Longitude", "PWCent_Latitude", "eligible_at_reference_year",
        "sample_entry_year", "sample_exit_year", "threshold_observed",
    }
    require_columns(population_panel, population_required, source_name="WUP F21 panel")
    reject_duplicate_keys(population_panel, ["city_id", "year"], source_name="WUP F21 panel")
    base = population_panel[
        [
            "city_id", "year", "population", "observation_type", "ISO3_Code", "City_Name",
            "PWCent_Longitude", "PWCent_Latitude", "eligible_at_reference_year",
            "sample_entry_year", "sample_exit_year", "threshold_observed",
        ]
    ].copy()
    area = _metric_subset(area_panel, ["land_area_km2"], source_name="WUP F25 panel")
    built = _metric_subset(
        built_per_capita_panel,
        ["built_up_area_m2_per_capita", "reported_zero"],
        source_name="WUP F30 panel",
    )
    density = _metric_subset(
        density_panel, ["population_density_per_km2"], source_name="WUP F34 panel"
    )
    expected_rows = len(base)
    panel = base.merge(area, on=["city_id", "year"], validate="one_to_one")
    panel = panel.merge(built, on=["city_id", "year"], validate="one_to_one")
    panel = panel.merge(density, on=["city_id", "year"], validate="one_to_one")
    if len(panel) != expected_rows or any(
        len(frame) != expected_rows for frame in [area, built, density]
    ):
        raise SourceSchemaError("WUP F21/F25/F30/F34 city-year coverage differs")
    validate_density_identity(population_panel, area_panel, density_panel)
    panel["built_up_area_m2"] = (
        panel["population"] * panel["built_up_area_m2_per_capita"]
    )
    panel["built_up_area_status"] = "derived_f21_times_f30"
    zero = panel["reported_zero"]
    panel.loc[zero, "built_up_area_m2"] = pd.NA
    panel.loc[zero, "built_up_area_status"] = "publisher_zero_excluded"
    panel["built_up_share_of_land"] = panel["built_up_area_m2"] / (
        panel["land_area_km2"] * 1_000_000
    )
    invalid_share = panel["built_up_share_of_land"].dropna().gt(1)
    if invalid_share.any():
        raise SourceSchemaError("Derived WUP built-up area exceeds land area")
    reject_duplicate_keys(panel, ["city_id", "year"], source_name="assembled WUP panel")
    return panel.sort_values(["city_id", "year"]).reset_index(drop=True)
