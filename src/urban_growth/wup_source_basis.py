"""WUP H1 robustness checks by documented population-input source basis."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.contemporaneous_baseline import (
    attach_contemporaneous_country_recent_growth,
)
from urban_growth.forecast import rolling_origin_splits
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

M01_REQUIRED = {
    "ISO3_Code",
    "Location",
    "DataProcessType",
    "DataProcess",
    "DataStatusName",
    "Input_Pop_year",
    "Input_Pop_level",
    "Input_Pop_source",
}


def read_wup_m01_source_metadata(path: str) -> pd.DataFrame:
    """Read the WUP M01 country-level GHSL population-input metadata."""
    frame = pd.read_excel(path, sheet_name="Input_Metadata")
    require_columns(frame, M01_REQUIRED, source_name="WUP 2025 M01")
    selected = frame[list(M01_REQUIRED)].rename(
        columns={
            "ISO3_Code": "country_code",
            "Location": "source_country_name",
            "DataProcessType": "source_process_type",
            "DataProcess": "source_process",
            "DataStatusName": "source_status",
            "Input_Pop_year": "source_population_year",
            "Input_Pop_level": "source_admin_level",
            "Input_Pop_source": "source_citation",
        }
    )
    reject_duplicate_keys(selected, ["country_code"], source_name="WUP 2025 M01")
    if selected["country_code"].isna().any():
        raise SourceSchemaError("WUP M01 country codes must be complete")
    selected["source_population_year"] = pd.to_numeric(
        selected["source_population_year"], errors="coerce"
    ).astype("Int64")
    selected["source_admin_level"] = pd.to_numeric(
        selected["source_admin_level"], errors="coerce"
    ).astype("Int64")
    allowed = {"Census", "Register", "Estimate"}
    unknown = sorted(set(selected["source_process_type"].dropna()) - allowed)
    if unknown:
        raise SourceSchemaError(f"Unknown WUP M01 process types: {', '.join(unknown)}")
    return selected


def attach_wup_source_basis(
    intervals: pd.DataFrame,
    metadata: pd.DataFrame,
) -> pd.DataFrame:
    """Attach country-input lineage while leaving city-level basis unresolved."""
    require_columns(
        intervals,
        {"city_id", "country_code", "period_start"},
        source_name="WUP source-basis intervals",
    )
    require_columns(
        metadata,
        {
            "country_code",
            "source_process_type",
            "source_population_year",
            "source_admin_level",
        },
        source_name="WUP M01 normalized metadata",
    )
    reject_duplicate_keys(metadata, ["country_code"], source_name="WUP M01 metadata")
    result = intervals.merge(metadata, on="country_code", how="left", validate="many_to_one")
    resolved = result["source_population_year"].notna() & result["source_process_type"].notna()
    result["country_input_resolution"] = np.where(resolved, "resolved", "unresolved")
    result["city_source_resolution"] = np.where(resolved, "country_proxy_only", "unresolved")
    result["city_direct_observation_status"] = "unresolved"
    result["source_population_year_distance"] = (
        result["period_start"] - result["source_population_year"]
    ).astype("Int64")
    result["source_granularity"] = result["source_admin_level"].map(
        lambda value: f"admin_{int(value)}" if pd.notna(value) else "unresolved"
    )

    process = result["source_process_type"].astype("string").str.lower()
    distance = result["source_population_year_distance"]
    result["source_process_stratum"] = process.fillna("unresolved")
    result["source_recency_stratum"] = "unresolved"
    result.loc[resolved & distance.lt(0), "source_recency_stratum"] = "post_origin_input"
    direct = process.isin(["census", "register"])
    result.loc[resolved & distance.ge(0) & direct & distance.le(10), "source_recency_stratum"] = (
        "recent_direct_input"
    )
    result.loc[resolved & distance.gt(10) & direct, "source_recency_stratum"] = "stale_direct_input"
    result.loc[resolved & distance.ge(0) & ~direct, "source_recency_stratum"] = "estimate_input"
    return result


def source_basis_classification_rows(intervals: pd.DataFrame) -> pd.DataFrame:
    """Return one explicit source-basis classification per evaluated city-origin row."""
    columns = [
        "city_id",
        "country_code",
        "period_start",
        "period_end",
        "source_process_type",
        "source_population_year",
        "source_admin_level",
        "source_population_year_distance",
        "source_process_stratum",
        "source_recency_stratum",
        "source_granularity",
        "country_input_resolution",
        "city_source_resolution",
        "city_direct_observation_status",
    ]
    require_columns(intervals, set(columns), source_name="WUP classified H1 rows")
    result = intervals[columns].copy()
    reject_duplicate_keys(
        result,
        ["city_id", "period_start", "period_end"],
        source_name="WUP source-basis classification rows",
    )
    return result.sort_values(["period_start", "country_code", "city_id"]).reset_index(drop=True)


def _slope(x: pd.Series, y: pd.Series, country: pd.Series, weighting: str) -> float:
    if weighting == "country_balanced":
        weights = 1.0 / country.groupby(country).transform("size")
    else:
        weights = pd.Series(1.0, index=x.index)
    denominator = float(np.sum(weights * x.pow(2)))
    if denominator <= 0:
        return np.nan
    return float(np.sum(weights * x * y) / denominator)


def _losses(
    actual: pd.Series,
    predicted: pd.Series,
    country: pd.Series,
    weighting: str,
) -> tuple[float, float]:
    error = predicted.to_numpy() - actual.to_numpy()
    frame = pd.DataFrame({"country": country.to_numpy(), "error": error})
    if weighting == "row_weighted":
        return float(np.abs(error).mean()), float(np.sqrt(np.square(error).mean()))
    country_loss = (
        frame.assign(
            absolute_error=lambda value: value["error"].abs(),
            squared_error=lambda value: value["error"].pow(2),
        )
        .groupby("country")[["absolute_error", "squared_error"]]
        .mean()
    )
    return float(country_loss["absolute_error"].mean()), float(
        np.sqrt(country_loss["squared_error"].mean())
    )


def evaluate_wup_h1_by_source_basis(
    classified_intervals: pd.DataFrame,
    origins: list[int],
    *,
    outcome_column: str = "future_growth",
) -> pd.DataFrame:
    """Evaluate the nested contemporaneous H1 model within source-basis strata."""
    working = attach_contemporaneous_country_recent_growth(classified_intervals)
    peer = "country_contemporaneous_recent_growth_leave_city_out"
    required = {
        "city_id",
        "country_code",
        "period_start",
        "period_end",
        "population_start",
        "recent_growth",
        outcome_column,
        peer,
        "source_recency_stratum",
        "source_process_stratum",
        "source_granularity",
    }
    require_columns(working, required, source_name="WUP source-basis H1 panel")
    if not origins or len(origins) != len(set(origins)):
        raise SourceSchemaError("WUP source-basis origins must be unique and non-empty")

    rows: list[dict[str, object]] = []
    stratifications = {
        "recency": "source_recency_stratum",
        "process_type": "source_process_stratum",
        "admin_level": "source_granularity",
    }
    for origin, train_index, test_index in rolling_origin_splits(working, sorted(origins)):
        origin_train = working.loc[train_index].copy()
        origin_test = working.loc[test_index].copy()
        finite = ["recent_growth", peer, outcome_column, "population_start"]
        origin_train = origin_train.loc[np.isfinite(origin_train[finite]).all(axis=1)]
        origin_test = origin_test.loc[np.isfinite(origin_test[finite]).all(axis=1)]
        total_population = float(origin_test["population_start"].sum())
        for stratification, column in stratifications.items():
            for stratum, test in origin_test.groupby(column, dropna=False, sort=True):
                train = origin_train.loc[origin_train[column].eq(stratum)].copy()
                for weighting in ["row_weighted", "country_balanced"]:
                    common = {
                        "origin": int(origin),
                        "stratification": stratification,
                        "stratum": str(stratum),
                        "weighting": weighting,
                        "n": len(test),
                        "country_count": int(test["country_code"].nunique()),
                        "population": float(test["population_start"].sum()),
                        "population_coverage_fraction": (
                            float(test["population_start"].sum()) / total_population
                            if total_population > 0
                            else np.nan
                        ),
                        "matched_train_n": len(train),
                        "training_precedes_origin": True,
                        "test_rows_identical": True,
                        "city_direct_observation_status": "unresolved",
                        "source_scope": "country_input_proxy",
                    }
                    if train.empty:
                        rows.append(
                            {
                                **common,
                                "evaluation_status": "insufficient_prior_stratum_training",
                                "beta": np.nan,
                                "baseline_mae": np.nan,
                                "augmented_mae": np.nan,
                                "mae_delta_augmented_minus_baseline": np.nan,
                                "baseline_rmse": np.nan,
                                "augmented_rmse": np.nan,
                                "rmse_delta_augmented_minus_baseline": np.nan,
                                "augmented_improves_mae": pd.NA,
                                "augmented_improves_rmse": pd.NA,
                            }
                        )
                        continue
                    train_x = train["recent_growth"] - train[peer]
                    train_y = train[outcome_column] - train[peer]
                    test_x = test["recent_growth"] - test[peer]
                    beta = _slope(train_x, train_y, train["country_code"], weighting)
                    if not np.isfinite(beta):
                        continue
                    baseline = test[peer]
                    augmented = baseline + beta * test_x
                    baseline_mae, baseline_rmse = _losses(
                        test[outcome_column], baseline, test["country_code"], weighting
                    )
                    augmented_mae, augmented_rmse = _losses(
                        test[outcome_column], augmented, test["country_code"], weighting
                    )
                    rows.append(
                        {
                            **common,
                            "evaluation_status": "evaluated",
                            "beta": beta,
                            "baseline_mae": baseline_mae,
                            "augmented_mae": augmented_mae,
                            "mae_delta_augmented_minus_baseline": (augmented_mae - baseline_mae),
                            "baseline_rmse": baseline_rmse,
                            "augmented_rmse": augmented_rmse,
                            "rmse_delta_augmented_minus_baseline": (augmented_rmse - baseline_rmse),
                            "augmented_improves_mae": augmented_mae < baseline_mae,
                            "augmented_improves_rmse": augmented_rmse < baseline_rmse,
                        }
                    )
    if not rows:
        raise SourceSchemaError("No WUP source-basis H1 evaluations were produced")
    return (
        pd.DataFrame(rows)
        .sort_values(["origin", "stratification", "stratum", "weighting"])
        .reset_index(drop=True)
    )
