"""Frozen H1 WUP rolling-origin out-of-sample evidence builder.

Implements the preregistered H1 protocol from issue #211. The evidence path is
intentionally stricter than the older contemporaneous-baseline diagnostic:
singleton-country rows are excluded rather than replaced by a global fallback.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

from urban_growth.adapters.wup import read_f21_city_population
from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

SPEC_VERSION = "H1-WUP-OOS-V1"
SOURCE_ID = "un_wup_2025_cities"
WUP_VINTAGE = "WUP_2025_F21"
INCONCLUSIVE_RESULT_ID = "RESULT-H1-OOS-WUP-INCONCLUSIVE-V1"
COMPLETE_RESULT_ID = "RESULT-H1-OOS-WUP-COMPLETE-V1"
TEST_ID = "TEST-H1-PERSISTENCE-OOS"


@dataclass(frozen=True)
class H1OOSProtocol:
    horizon_years: int = 5
    growth_window_years: int = 5
    origin_step_years: int = 5
    estimate_end_year: int = 2025
    minimum_training_rows: int = 100
    minimum_training_countries: int = 30
    rmse_improvement_threshold: float = 0.05
    mae_difference_threshold: float = 0.0


PROTOCOL = H1OOSProtocol()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _annualized_log_growth(
    start: pd.Series,
    end: pd.Series,
    years: int,
) -> pd.Series:
    if years <= 0:
        raise SourceSchemaError("Growth interval must be positive")
    if start.le(0).any() or end.le(0).any():
        raise SourceSchemaError("H1 OOS growth requires strictly positive populations")
    return (np.log(end) - np.log(start)) / years


def build_five_year_intervals(city_year_panel: pd.DataFrame) -> pd.DataFrame:
    """Build estimate-only 5-year intervals before origin eligibility filtering."""
    required = {"city_id", "ISO3_Code", "year", "population", "observation_type"}
    require_columns(city_year_panel, required, source_name="H1 WUP city-year panel")
    reject_duplicate_keys(
        city_year_panel,
        ["city_id", "year"],
        source_name="H1 WUP city-year panel",
    )

    source = city_year_panel.copy()
    source["year"] = pd.to_numeric(source["year"], errors="raise").astype(int)
    source["population"] = pd.to_numeric(source["population"], errors="coerce")
    available_years = sorted(set(source["year"]))
    origins = [
        year
        for year in available_years
        if year % PROTOCOL.origin_step_years == 0
        and year - PROTOCOL.growth_window_years in available_years
        and year + PROTOCOL.horizon_years in available_years
        and year + PROTOCOL.horizon_years <= PROTOCOL.estimate_end_year
    ]
    indexed = source.set_index(["city_id", "year"])
    frames: list[pd.DataFrame] = []
    for origin in origins:
        lag = origin - PROTOCOL.growth_window_years
        target = origin + PROTOCOL.horizon_years
        city_ids = indexed.index.get_level_values("city_id").unique()
        keys = pd.MultiIndex.from_product(
            [city_ids, [lag, origin, target]],
            names=["city_id", "year"],
        )
        complete = indexed.reindex(keys).reset_index()
        wide = complete.pivot(index="city_id", columns="year")
        valid = wide["population"].notna().all(axis=1)
        valid &= wide[("observation_type", target)].eq("estimate")
        valid &= wide[("observation_type", origin)].eq("estimate")
        valid &= wide[("observation_type", lag)].eq("estimate")
        wide = wide.loc[valid]
        if wide.empty:
            continue
        frame = pd.DataFrame(index=wide.index)
        frame["country_code"] = wide[("ISO3_Code", origin)]
        frame["period_start"] = origin
        frame["period_end"] = target
        frame["horizon_years"] = PROTOCOL.horizon_years
        frame["growth_window_years"] = PROTOCOL.growth_window_years
        frame["population_lag"] = wide[("population", lag)]
        frame["population_origin"] = wide[("population", origin)]
        frame["population_target"] = wide[("population", target)]
        frame["recent_growth"] = _annualized_log_growth(
            frame["population_lag"],
            frame["population_origin"],
            PROTOCOL.growth_window_years,
        )
        frame["future_growth"] = _annualized_log_growth(
            frame["population_origin"],
            frame["population_target"],
            PROTOCOL.horizon_years,
        )
        if "City_Name" in source.columns:
            frame["city_name"] = wide[("City_Name", origin)]
        frames.append(frame.reset_index())
    if not frames:
        raise SourceSchemaError(
            "No estimate-only 5-year WUP intervals satisfy the frozen H1 rules"
        )
    result = pd.concat(frames, ignore_index=True)
    if result["country_code"].isna().any():
        raise SourceSchemaError("H1 OOS interval lacks ISO3 country code")
    reject_duplicate_keys(
        result,
        ["city_id", "period_start"],
        source_name="H1 WUP OOS intervals",
    )
    return result.sort_values(
        ["period_start", "country_code", "city_id"]
    ).reset_index(drop=True)


def attach_strict_country_peer_growth(
    intervals: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Attach same-origin country LOO growth and exclude singleton countries."""
    required = {"city_id", "country_code", "period_start", "recent_growth"}
    require_columns(intervals, required, source_name="H1 OOS intervals")
    working = intervals.copy()
    grouped = working.groupby(["period_start", "country_code"])["recent_growth"]
    working["_country_sum"] = grouped.transform("sum")
    working["_country_count"] = grouped.transform("count")
    singleton = working["_country_count"].lt(2)
    exclusions = (
        working.loc[singleton, ["period_start", "country_code"]]
        .value_counts(sort=False)
        .rename("excluded_city_rows")
        .reset_index()
    )
    retained = working.loc[~singleton].copy()
    retained["country_peer_recent_growth_loo"] = (
        retained["_country_sum"] - retained["recent_growth"]
    ) / (retained["_country_count"] - 1)
    retained["focal_city_recent_growth_deviation"] = (
        retained["recent_growth"] - retained["country_peer_recent_growth_loo"]
    )
    retained["country_peer_count"] = retained["_country_count"] - 1
    retained["country_peer_leave_city_out"] = True
    retained["country_peer_uses_future_value"] = False
    retained = retained.drop(columns=["_country_sum", "_country_count"])
    return retained.reset_index(drop=True), exclusions


def derive_eligible_origins(intervals: pd.DataFrame) -> pd.DataFrame:
    """Apply the frozen minimum training-row and country gates."""
    rows: list[dict[str, Any]] = []
    for origin in sorted(set(intervals["period_start"])):
        train = intervals.loc[intervals["period_end"] <= origin]
        test = intervals.loc[intervals["period_start"] == origin]
        train_n = len(train)
        train_countries = int(train["country_code"].nunique())
        eligible = (
            train_n >= PROTOCOL.minimum_training_rows
            and train_countries >= PROTOCOL.minimum_training_countries
            and not test.empty
        )
        rows.append(
            {
                "origin": int(origin),
                "training_rows": train_n,
                "training_countries": train_countries,
                "scoring_rows": len(test),
                "scoring_countries": int(test["country_code"].nunique()),
                "eligible": eligible,
            }
        )
    return pd.DataFrame(rows)


def _fit_ols(frame: pd.DataFrame, features: list[str]) -> np.ndarray:
    columns = [np.ones(len(frame)), *(frame[name].to_numpy() for name in features)]
    x = np.column_stack(columns)
    y = frame["future_growth"].to_numpy()
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise SourceSchemaError("H1 OOS OLS received non-finite training values")
    beta, _, rank, _ = np.linalg.lstsq(x, y, rcond=None)
    if rank != x.shape[1]:
        raise SourceSchemaError("H1 OOS OLS design matrix is rank deficient")
    return beta


def _predict(
    frame: pd.DataFrame,
    features: list[str],
    beta: np.ndarray,
) -> np.ndarray:
    columns = [np.ones(len(frame)), *(frame[name].to_numpy() for name in features)]
    return np.column_stack(columns) @ beta


def fit_rolling_oos(
    intervals: pd.DataFrame,
    *,
    construction_commit: str,
    panel_spec_version: str = SPEC_VERSION,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fit locked B0/B1 OLS models at each eligible origin."""
    eligibility = derive_eligible_origins(intervals)
    eligible_origins = eligibility.loc[
        eligibility["eligible"], "origin"
    ].astype(int).tolist()
    if not eligible_origins:
        raise SourceSchemaError(
            "No origins pass the frozen 100-row/30-country training gate"
        )
    rows: list[pd.DataFrame] = []
    b0_features = ["country_peer_recent_growth_loo"]
    b1_features = [
        "country_peer_recent_growth_loo",
        "focal_city_recent_growth_deviation",
    ]
    needed = ["future_growth", *b1_features]
    for origin in eligible_origins:
        train = intervals.loc[intervals["period_end"] <= origin]
        test = intervals.loc[intervals["period_start"] == origin]
        train = train.dropna(subset=needed).copy()
        test = test.dropna(subset=needed).copy()
        train = train.loc[np.isfinite(train[needed]).all(axis=1)]
        test = test.loc[np.isfinite(test[needed]).all(axis=1)]
        if len(train) < PROTOCOL.minimum_training_rows:
            raise SourceSchemaError(
                "Eligible origin lost rows after joint B0/B1 matching"
            )
        if train["country_code"].nunique() < PROTOCOL.minimum_training_countries:
            raise SourceSchemaError(
                "Eligible origin lost countries after joint B0/B1 matching"
            )
        if test.empty:
            raise SourceSchemaError("Eligible origin has no jointly matched scoring rows")
        b0_beta = _fit_ols(train, b0_features)
        b1_beta = _fit_ols(train, b1_features)
        out = test.copy()
        out["b0_prediction"] = _predict(test, b0_features, b0_beta)
        out["b1_prediction"] = _predict(test, b1_features, b1_beta)
        out["b0_error"] = out["b0_prediction"] - out["future_growth"]
        out["b1_error"] = out["b1_prediction"] - out["future_growth"]
        out["b0_absolute_error"] = out["b0_error"].abs()
        out["b1_absolute_error"] = out["b1_error"].abs()
        out["b0_squared_error"] = out["b0_error"].pow(2)
        out["b1_squared_error"] = out["b1_error"].pow(2)
        out["training_rows"] = len(train)
        out["training_countries"] = int(train["country_code"].nunique())
        out["training_max_period_end"] = int(train["period_end"].max())
        out["training_precedes_or_equals_origin"] = (
            out["training_max_period_end"] <= origin
        )
        out["b0_b1_training_rows_identical"] = True
        out["b0_b1_scoring_rows_identical"] = True
        out["wup_vintage"] = WUP_VINTAGE
        out["construction_commit"] = construction_commit
        out["panel_spec_version"] = panel_spec_version
        rows.append(out)
    panel = pd.concat(rows, ignore_index=True)
    reject_duplicate_keys(
        panel,
        ["city_id", "period_start"],
        source_name="H1 OOS scoring panel",
    )
    if not panel["training_precedes_or_equals_origin"].all():
        raise SourceSchemaError("H1 OOS training leakage detected")
    return (
        panel.sort_values(["period_start", "country_code", "city_id"]).reset_index(
            drop=True
        ),
        eligibility,
    )


def _losses(frame: pd.DataFrame, weight: pd.Series) -> dict[str, float]:
    if not np.isclose(float(weight.sum()), 1.0):
        raise SourceSchemaError("H1 OOS loss weights must sum to one")
    result: dict[str, float] = {}
    for model in ("b0", "b1"):
        result[f"{model}_mae"] = float(
            np.sum(weight * frame[f"{model}_absolute_error"])
        )
        result[f"{model}_rmse"] = float(
            np.sqrt(np.sum(weight * frame[f"{model}_squared_error"]))
        )
    result["relative_rmse_improvement"] = (
        (result["b0_rmse"] - result["b1_rmse"]) / result["b0_rmse"]
        if result["b0_rmse"] > 0
        else np.nan
    )
    result["mae_difference"] = result["b1_mae"] - result["b0_mae"]
    return result


def _gate_fields(metrics: dict[str, float]) -> dict[str, bool]:
    rmse_pass = (
        metrics["relative_rmse_improvement"]
        >= PROTOCOL.rmse_improvement_threshold
    )
    mae_pass = metrics["mae_difference"] <= PROTOCOL.mae_difference_threshold
    return {
        "rmse_condition_passed": bool(rmse_pass),
        "mae_condition_passed": bool(mae_pass),
        "gate_passed": bool(rmse_pass and mae_pass),
    }


def summarize_oos(panel: pd.DataFrame) -> pd.DataFrame:
    """Summarize each origin, then aggregate with equal origin weights."""
    rows: list[dict[str, Any]] = []
    origins = sorted(set(panel["period_start"]))
    if not origins:
        raise SourceSchemaError("Cannot summarize an empty H1 OOS panel")
    for origin in origins:
        group = panel.loc[panel["period_start"] == origin].copy()
        country_sizes = group.groupby("country_code")["city_id"].transform("size")
        country_count = int(group["country_code"].nunique())
        weights = {
            "country_balanced": 1.0 / (country_count * country_sizes),
            "row_weighted": pd.Series(1.0 / len(group), index=group.index),
        }
        for weighting, weight in weights.items():
            metrics = _losses(group, weight)
            rows.append(
                {
                    "scope": "origin",
                    "origin": int(origin),
                    "weighting": weighting,
                    "n_cities": len(group),
                    "n_countries": country_count,
                    **metrics,
                    **_gate_fields(metrics),
                }
            )
    origin_count = len(origins)
    for weighting in ("country_balanced", "row_weighted"):
        aggregate_weights = pd.Series(0.0, index=panel.index)
        for origin in origins:
            group = panel.loc[panel["period_start"] == origin]
            if weighting == "country_balanced":
                country_sizes = group.groupby("country_code")["city_id"].transform(
                    "size"
                )
                origin_weights = 1.0 / (
                    group["country_code"].nunique() * country_sizes
                )
            else:
                origin_weights = pd.Series(1.0 / len(group), index=group.index)
            aggregate_weights.loc[group.index] = origin_weights / origin_count
        metrics = _losses(panel, aggregate_weights)
        rows.append(
            {
                "scope": "aggregate",
                "origin": pd.NA,
                "weighting": weighting,
                "n_cities": len(panel),
                "n_countries": int(panel["country_code"].nunique()),
                **metrics,
                **_gate_fields(metrics),
            }
        )
    return pd.DataFrame(rows)


def _result_payload(
    summary: pd.DataFrame,
    manifest: dict[str, Any],
    *,
    complete: bool,
) -> dict[str, Any]:
    primary = summary.loc[
        summary["scope"].eq("aggregate")
        & summary["weighting"].eq("country_balanced")
    ].iloc[0]
    result_id = COMPLETE_RESULT_ID if complete else INCONCLUSIVE_RESULT_ID
    metrics = {
        "relative_rmse_improvement": float(primary["relative_rmse_improvement"])
    }
    if complete:
        metrics["mae_difference"] = float(primary["mae_difference"])
    sample = {
        "origins": manifest["eligible_origins"],
        "panel_sha256": manifest["panel_sha256"],
        "panel_spec_version": manifest["panel_spec_version"],
    }
    if complete:
        sample["limitation"] = (
            "Historical pseudo-OOS using harmonized WUP series; passing this gate "
            "does not substitute for external direct-count census validation."
        )
    return {
        "id": result_id,
        "type": "result",
        "title": (
            "H1 WUP rolling-origin OOS completed result"
            if complete
            else "H1 WUP OOS deliberately incomplete W2 probe"
        ),
        "canonical_name": (
            "H1 WUP OOS completed result v1"
            if complete
            else "H1 WUP OOS W2 inconclusive probe v1"
        ),
        "aliases": [],
        "test": TEST_ID,
        "status": "completed",
        "executed_at": manifest["generated_at"],
        "metrics": metrics,
        "execution": {
            "commit": manifest["construction_commit"],
            "environment_lock": manifest["environment_lock_sha256"],
            "command": manifest["construction_command"],
        },
        "sample": sample,
        "inputs": {
            "datasets": ["DATA-WUP-CITY-POP"],
            "artifacts": [manifest["panel_path"]],
        },
        "relations": [],
    }


def write_evidence_package(
    f21_path: Path,
    output_dir: Path,
    *,
    construction_commit: str,
    repo_root: Path,
) -> dict[str, Any]:
    """Build panel, summaries, lineage manifest, and staged result payloads."""
    output_dir.mkdir(parents=True, exist_ok=True)
    city = read_f21_city_population(str(f21_path))
    intervals = build_five_year_intervals(city)
    strict, exclusions = attach_strict_country_peer_growth(intervals)
    panel, eligibility = fit_rolling_oos(
        strict,
        construction_commit=construction_commit,
    )
    summary = summarize_oos(panel)

    panel_path = output_dir / "h1_oos_rows.parquet"
    try:
        panel.to_parquet(panel_path, index=False)
    except (ImportError, ModuleNotFoundError) as exc:
        raise SourceSchemaError(
            "Parquet output requires an installed pandas parquet engine"
        ) from exc
    summary_path = output_dir / "h1_oos_summary.csv"
    exclusions_path = output_dir / "h1_oos_singleton_exclusions.csv"
    eligibility_path = output_dir / "h1_oos_origin_eligibility.csv"
    summary.to_csv(summary_path, index=False)
    exclusions.to_csv(exclusions_path, index=False)
    eligibility.to_csv(eligibility_path, index=False)

    lock_path = repo_root / "uv.lock"
    eligible_origins = eligibility.loc[
        eligibility["eligible"], "origin"
    ].astype(int).tolist()
    generated_at = datetime.now(UTC).isoformat()
    command = (
        "python -m urban_growth.h1_oos build "
        f"--f21 {f21_path} --output-dir {output_dir} "
        f"--commit {construction_commit}"
    )
    manifest: dict[str, Any] = {
        "panel_spec_version": SPEC_VERSION,
        "source_id": SOURCE_ID,
        "wup_vintage": WUP_VINTAGE,
        "source_path": str(f21_path),
        "source_sha256": _sha256(f21_path),
        "construction_commit": construction_commit,
        "environment_lock": "uv.lock",
        "environment_lock_sha256": _sha256(lock_path),
        "construction_command": command,
        "generated_at": generated_at,
        "protocol": asdict(PROTOCOL),
        "eligible_origins": eligible_origins,
        "equal_origin_aggregation": True,
        "balanced_city_panel_required": False,
        "training_pooling": (
            "all_prior_city_origin_rows_with_outcome_observable_by_origin"
        ),
        "within_training_period_stratification": False,
        "singleton_policy": "exclude_at_each_row_origin_no_global_fallback",
        "reserved_result_ids": [INCONCLUSIVE_RESULT_ID, COMPLETE_RESULT_ID],
        "panel_path": str(panel_path),
        "panel_sha256": _sha256(panel_path),
        "summary_path": str(summary_path),
        "summary_sha256": _sha256(summary_path),
        "singleton_exclusions_path": str(exclusions_path),
        "origin_eligibility_path": str(eligibility_path),
        "limitations": [
            (
                "WUP historical pseudo-OOS series may be smoother than direct-count "
                "census observations."
            ),
            (
                "A passing WUP gate does not substitute for external direct-count "
                "validation."
            ),
        ],
    }
    manifest_path = output_dir / "h1_oos_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    probe_path = output_dir / f"{INCONCLUSIVE_RESULT_ID}.yaml"
    complete_path = output_dir / f"{COMPLETE_RESULT_ID}.yaml"
    probe_path.write_text(
        yaml.safe_dump(
            _result_payload(summary, manifest, complete=False),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    complete_path.write_text(
        yaml.safe_dump(
            _result_payload(summary, manifest, complete=True),
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build the frozen H1 WUP OOS evidence package"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build")
    build.add_argument("--f21", required=True, type=Path)
    build.add_argument("--output-dir", required=True, type=Path)
    build.add_argument("--commit", required=True)
    build.add_argument("--repo-root", type=Path, default=Path.cwd())
    return parser


def main() -> None:
    args = _parser().parse_args()
    if args.command == "build":
        manifest = write_evidence_package(
            args.f21,
            args.output_dir,
            construction_commit=args.commit,
            repo_root=args.repo_root,
        )
        print(json.dumps(manifest, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
