"""Vintage-correct forecast diagnostics across explicitly different WUP definitions."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.forecast import cluster_bootstrap_paired_difference, score_forecast
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


def reciprocal_nearest_crosswalk(
    vintage_panel: pd.DataFrame,
    current_panel: pd.DataFrame,
    *,
    maximum_distance_km: float = 10.0,
) -> pd.DataFrame:
    """Match cities only when they are reciprocal geographic nearest neighbours."""
    vintage_required = {
        "city_id", "country_location_id", "city_name", "latitude", "longitude"
    }
    current_required = {
        "city_id", "LocID", "City_Name", "PWCent_Latitude", "PWCent_Longitude"
    }
    require_columns(vintage_panel, vintage_required, source_name="WUP vintage panel")
    require_columns(current_panel, current_required, source_name="WUP current panel")
    if maximum_distance_km <= 0:
        raise SourceSchemaError("Crosswalk distance must be positive")
    old = vintage_panel[list(vintage_required)].drop_duplicates()
    new = current_panel[list(current_required)].drop_duplicates()
    reject_duplicate_keys(old, ["city_id"], source_name="WUP vintage city metadata")
    reject_duplicate_keys(new, ["city_id"], source_name="WUP current city metadata")
    rows: list[dict[str, float | int | str]] = []
    for country, old_group in old.groupby("country_location_id", sort=True):
        new_group = new.loc[new["LocID"].eq(country)]
        if new_group.empty:
            continue
        old_lat = np.radians(old_group["latitude"].to_numpy())[:, None]
        old_lon = np.radians(old_group["longitude"].to_numpy())[:, None]
        new_lat = np.radians(new_group["PWCent_Latitude"].to_numpy())[None, :]
        new_lon = np.radians(new_group["PWCent_Longitude"].to_numpy())[None, :]
        haversine = np.sin((new_lat - old_lat) / 2) ** 2 + (
            np.cos(old_lat) * np.cos(new_lat) * np.sin((new_lon - old_lon) / 2) ** 2
        )
        distances = 6371.0 * 2 * np.arcsin(np.sqrt(haversine))
        old_to_new = distances.argmin(axis=1)
        new_to_old = distances.argmin(axis=0)
        for old_position, new_position in enumerate(old_to_new):
            distance = float(distances[old_position, new_position])
            if new_to_old[new_position] != old_position or distance > maximum_distance_km:
                continue
            old_row = old_group.iloc[old_position]
            new_row = new_group.iloc[new_position]
            rows.append(
                {
                    "vintage_city_id": old_row["city_id"],
                    "current_city_id": new_row["city_id"],
                    "country_location_id": country,
                    "vintage_city_name": old_row["city_name"],
                    "current_city_name": new_row["City_Name"],
                    "distance_km": distance,
                    "match_method": "reciprocal_nearest_within_country",
                }
            )
    if not rows:
        raise SourceSchemaError("No reciprocal WUP vintage crosswalk matches")
    result = pd.DataFrame(rows)
    reject_duplicate_keys(result, ["vintage_city_id"], source_name="WUP vintage crosswalk")
    reject_duplicate_keys(result, ["current_city_id"], source_name="WUP vintage crosswalk")
    return result.sort_values(["country_location_id", "vintage_city_id"]).reset_index(drop=True)


def evaluate_wup2018_vintage(
    vintage_panel: pd.DataFrame,
    current_panel: pd.DataFrame,
    crosswalk: pd.DataFrame,
    *,
    origin_year: int = 2018,
    lookback_years: int = 5,
    horizon_years: int = 5,
    distance_thresholds: tuple[float, ...] = (1.0, 5.0, 10.0),
    population_agreement_thresholds: tuple[float | None, ...] = (None, 0.1, 0.2, 0.5),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Score the 2018 published projection against later revised estimates.

    Population-agreement restrictions use later-revision information and are
    sensitivities, not valid real-time sample-selection rules.
    """
    years = [origin_year - lookback_years, origin_year, origin_year + horizon_years]
    old = vintage_panel.loc[vintage_panel["year"].isin(years)].pivot(
        index="city_id", columns="year", values="population"
    )
    new = current_panel.loc[current_panel["year"].isin(years)].pivot(
        index="city_id", columns="year", values="population"
    )
    old.columns = [f"vintage_{year}" for year in old.columns]
    new.columns = [f"current_{year}" for year in new.columns]
    matched = crosswalk.merge(
        old, left_on="vintage_city_id", right_index=True, validate="one_to_one"
    ).merge(new, left_on="current_city_id", right_index=True, validate="one_to_one")
    value_columns = [
        *(f"vintage_{year}" for year in years), *(f"current_{year}" for year in years)
    ]
    matched = matched.dropna(subset=value_columns).copy()
    if matched.empty or (matched[value_columns] <= 0).any().any():
        raise SourceSchemaError("Vintage evaluation requires positive complete populations")
    matched["origin_absolute_log_difference"] = np.abs(
        np.log(matched[f"current_{origin_year}"])
        - np.log(matched[f"vintage_{origin_year}"])
    )
    matched["actual"] = (
        np.log(matched[f"current_{origin_year + horizon_years}"])
        - np.log(matched[f"current_{origin_year}"])
    ) / horizon_years
    matched["published_projection"] = (
        np.log(matched[f"vintage_{origin_year + horizon_years}"])
        - np.log(matched[f"vintage_{origin_year}"])
    ) / horizon_years
    matched["vintage_persistence"] = (
        np.log(matched[f"vintage_{origin_year}"])
        - np.log(matched[f"vintage_{origin_year - lookback_years}"])
    ) / lookback_years
    matched["retrospective_persistence"] = (
        np.log(matched[f"current_{origin_year}"])
        - np.log(matched[f"current_{origin_year - lookback_years}"])
    ) / lookback_years
    models = ["published_projection", "vintage_persistence", "retrospective_persistence"]
    metric_rows: list[dict[str, float | int | str]] = []
    error_frames: list[pd.DataFrame] = []
    for distance in distance_thresholds:
        for agreement in population_agreement_thresholds:
            sample = matched.loc[matched["distance_km"].le(distance)].copy()
            agreement_label = "unrestricted"
            if agreement is not None:
                sample = sample.loc[
                    sample["origin_absolute_log_difference"].le(np.log1p(agreement))
                ]
                agreement_label = f"within_{int(agreement * 100)}pct"
            if sample.empty:
                continue
            for model in models:
                metrics = score_forecast(sample["actual"], sample[model])
                metric_rows.append(
                    {
                        "origin": origin_year,
                        "target_end": origin_year + horizon_years,
                        "distance_threshold_km": distance,
                        "origin_population_agreement": agreement_label,
                        "selection_uses_later_revision": agreement is not None,
                        "model": model,
                        "n": metrics.n,
                        "countries": sample["country_location_id"].nunique(),
                        "mae": metrics.mae,
                        "rmse": metrics.rmse,
                        "bias": metrics.bias,
                        "directional_accuracy": metrics.directional_accuracy,
                    }
                )
            if distance == 5.0 and agreement_label in {"unrestricted", "within_20pct"}:
                long = sample.melt(
                    id_vars=["current_city_id", "country_location_id"],
                    value_vars=models[:2], var_name="model", value_name="predicted",
                )
                actual = sample.set_index("current_city_id")["actual"]
                long["actual"] = long["current_city_id"].map(actual)
                long["error"] = long["predicted"] - long["actual"]
                long["absolute_error"] = long["error"].abs()
                long["sample"] = agreement_label
                long = long.rename(
                    columns={"current_city_id": "city_id", "country_location_id": "country_code"}
                )
                long["origin"] = origin_year
                error_frames.append(long)
    metrics = pd.DataFrame(metric_rows)
    errors = pd.concat(error_frames, ignore_index=True)
    bootstrap = cluster_bootstrap_paired_difference(
        errors,
        model_a="published_projection",
        model_b="vintage_persistence",
        group_columns=["sample"],
    )
    return metrics, bootstrap
