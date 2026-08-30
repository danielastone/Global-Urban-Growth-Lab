"""Locked estimator hierarchy for dynamic city-growth panels."""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


@dataclass(frozen=True)
class EstimatorSpec:
    """Machine-readable declaration of an estimator's estimand and limitations."""

    estimator_id: str
    city_fixed_effects: bool
    bias_correction: str
    estimand: str
    role: str
    implemented: bool = True


ESTIMATOR_REGISTRY = (
    EstimatorSpec(
        "pooled_dynamic", False, "none", "between-and-within predictive association",
        "primary predictive benchmark",
    ),
    EstimatorSpec(
        "city_fe_dynamic", True, "none", "within-city dynamic association",
        "Nickell-biased diagnostic",
    ),
    EstimatorSpec(
        "half_panel_jackknife", True, "split-panel jackknife",
        "first-order finite-T-bias-corrected within-city association",
        "retrospective estimate conditional on simulation performance",
    ),
    EstimatorSpec(
        "restricted_dynamic_gmm", True, "restricted collapsed instruments",
        "within-city dynamic association", "sensitivity only", implemented=False,
    ),
)


def estimator_registry() -> pd.DataFrame:
    """Return the locked registry without allowing run-time estimator relabeling."""
    return pd.DataFrame([asdict(spec) for spec in ESTIMATOR_REGISTRY])


def common_dynamic_sample(
    frame: pd.DataFrame,
    *,
    outcome: str,
    lagged_outcome: str,
    covariates: list[str],
    city: str = "city_id",
    country: str = "country_code",
    period: str = "period",
    min_city_periods: int = 4,
) -> pd.DataFrame:
    """Construct one complete-case analytic sample before any estimator is fitted."""
    required = {outcome, lagged_outcome, city, country, period, *covariates}
    require_columns(frame, required, source_name="dynamic estimator panel")
    reject_duplicate_keys(frame, [city, period], source_name="dynamic estimator panel")
    if min_city_periods < 4:
        raise SourceSchemaError("Dynamic estimators require at least four periods per city")
    sample = frame.dropna(subset=sorted(required)).copy()
    numeric = [outcome, lagged_outcome, *covariates]
    if not np.isfinite(sample[numeric].to_numpy(dtype=float)).all():
        raise SourceSchemaError("Dynamic estimator inputs must be finite")
    sample["country_period"] = sample[country].astype(str) + "::" + sample[period].astype(str)
    previous_rows = -1
    while previous_rows != len(sample):
        previous_rows = len(sample)
        sample = sample.loc[
            sample.groupby(city)[city].transform("size").ge(min_city_periods)
        ]
        # A singleton country-period cell is absorbed perfectly and carries no allocation signal.
        sample = sample.loc[
            sample.groupby("country_period")["country_period"].transform("size").ge(2)
        ]
    if sample.empty:
        raise SourceSchemaError("No rows survive the locked dynamic common-sample rules")
    return sample.sort_values([city, period]).reset_index(drop=True)


def _design(
    sample: pd.DataFrame,
    *,
    outcome: str,
    lagged_outcome: str,
    covariates: list[str],
    city: str,
    city_fixed_effects: bool,
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    regressors = [lagged_outcome, *covariates]
    parts = [sample[regressors].astype(float)]
    country_period = pd.get_dummies(
        sample["country_period"], prefix="cp", drop_first=False, dtype=float
    )
    parts.append(country_period)
    if city_fixed_effects:
        parts.append(pd.get_dummies(sample[city], prefix="city", drop_first=True, dtype=float))
    design = pd.concat(parts, axis=1)
    return sample[outcome].to_numpy(dtype=float), design.to_numpy(), list(design.columns)


def _cluster_meat(x: np.ndarray, residual: np.ndarray, groups: pd.Series) -> np.ndarray:
    scores = x * residual[:, None]
    grouped = pd.DataFrame(scores).groupby(groups.astype(str).to_numpy(), sort=False).sum()
    return grouped.to_numpy().T @ grouped.to_numpy()


def _fit_ols(
    sample: pd.DataFrame,
    *,
    outcome: str,
    lagged_outcome: str,
    covariates: list[str],
    city: str,
    country: str,
    period: str,
    city_fixed_effects: bool,
) -> pd.DataFrame:
    y, x, names = _design(
        sample, outcome=outcome, lagged_outcome=lagged_outcome, covariates=covariates,
        city=city, city_fixed_effects=city_fixed_effects,
    )
    beta = np.linalg.lstsq(x, y, rcond=None)[0]
    residual = y - x @ beta
    bread = np.linalg.pinv(x.T @ x)
    country_meat = _cluster_meat(x, residual, sample[country])
    period_meat = _cluster_meat(x, residual, sample[period])
    intersection = sample[country].astype(str) + "::" + sample[period].astype(str)
    covariance = bread @ (
        country_meat + period_meat - _cluster_meat(x, residual, intersection)
    ) @ bread
    target_count = 1 + len(covariates)
    return pd.DataFrame(
        {
            "term": names[:target_count],
            "estimate": beta[:target_count],
            "std_error_country_period": np.sqrt(
                np.maximum(np.diag(covariance)[:target_count], 0.0)
            ),
            "n_rows": len(sample),
            "n_cities": sample[city].nunique(),
            "n_periods": sample[period].nunique(),
        }
    )


def fit_dynamic_hierarchy(
    sample: pd.DataFrame,
    *,
    outcome: str,
    lagged_outcome: str,
    covariates: list[str],
    city: str = "city_id",
    country: str = "country_code",
    period: str = "period",
) -> pd.DataFrame:
    """Fit pooled, city-FE, and split-panel-jackknife estimates on one full sample."""
    required = {outcome, lagged_outcome, city, country, period, "country_period", *covariates}
    require_columns(sample, required, source_name="dynamic common sample")
    pooled = _fit_ols(
        sample, outcome=outcome, lagged_outcome=lagged_outcome, covariates=covariates,
        city=city, country=country, period=period, city_fixed_effects=False,
    ).assign(estimator_id="pooled_dynamic")
    fixed = _fit_ols(
        sample, outcome=outcome, lagged_outcome=lagged_outcome, covariates=covariates,
        city=city, country=country, period=period, city_fixed_effects=True,
    ).assign(estimator_id="city_fe_dynamic")
    periods = sorted(sample[period].unique())
    if len(periods) < 4:
        raise SourceSchemaError("Half-panel jackknife requires at least four periods")
    midpoint = len(periods) // 2
    halves = [periods[:midpoint], periods[midpoint:]]
    half_estimates = []
    for half in halves:
        half_sample = sample.loc[sample[period].isin(half)].copy()
        if half_sample.groupby(city)[city].size().min() < 2:
            raise SourceSchemaError("Each jackknife half requires two observations per city")
        half_estimates.append(
            _fit_ols(
                half_sample, outcome=outcome, lagged_outcome=lagged_outcome,
                covariates=covariates, city=city, country=country, period=period,
                city_fixed_effects=True,
            ).set_index("term")["estimate"]
        )
    corrected = fixed.copy()
    corrected["estimate"] = 2 * fixed["estimate"] - (
        half_estimates[0].reindex(fixed["term"]).to_numpy()
        + half_estimates[1].reindex(fixed["term"]).to_numpy()
    ) / 2
    corrected["std_error_country_period"] = np.nan
    corrected["estimator_id"] = "half_panel_jackknife"
    result = pd.concat([pooled, fixed, corrected], ignore_index=True)
    result["inference_status"] = np.where(
        result["estimator_id"].eq("half_panel_jackknife"),
        "point estimate only; panel bootstrap required",
        "country-and-period two-way sandwich",
    )
    registry = estimator_registry()[["estimator_id", "estimand", "role", "bias_correction"]]
    return result.merge(registry, on="estimator_id", validate="many_to_one")


def estimator_disagreement_report(
    estimates: pd.DataFrame, *, practical_tolerance: float = 0.05
) -> pd.DataFrame:
    """Report, rather than hide, sign and practical-magnitude disagreement."""
    require_columns(
        estimates, {"estimator_id", "term", "estimate"}, source_name="estimator results"
    )
    wide = estimates.pivot(index="term", columns="estimator_id", values="estimate")
    required = {"pooled_dynamic", "city_fe_dynamic", "half_panel_jackknife"}
    if not required.issubset(wide.columns):
        raise SourceSchemaError("Disagreement report requires all three implemented estimators")
    report = wide.reset_index()
    values = report[sorted(required)]
    report["sign_disagreement"] = values.apply(
        lambda row: len(set(np.sign(row.loc[row.ne(0)]))) > 1, axis=1
    )
    report["max_pairwise_gap"] = values.max(axis=1) - values.min(axis=1)
    report["practical_disagreement"] = report["max_pairwise_gap"].gt(practical_tolerance)
    report["must_report_disagreement"] = (
        report["sign_disagreement"] | report["practical_disagreement"]
    )
    return report


def simulate_dynamic_hierarchy(
    *,
    persistence_values: tuple[float, ...] = (0.2, 0.6, 0.9),
    panel_lengths: tuple[int, ...] = (6, 8, 10),
    replications: int = 25,
    cities: int = 48,
    countries: int = 6,
    seed: int = 1729,
) -> pd.DataFrame:
    """Evaluate finite-T bias and RMSE over a declared persistence/length grid."""
    if cities % countries or cities // countries < 2:
        raise SourceSchemaError("Simulation requires at least two equal-count cities per country")
    if replications < 2 or min(panel_lengths) < 4:
        raise SourceSchemaError("Simulation requires two replications and four panel periods")
    rng = np.random.default_rng(seed)
    records: list[dict[str, float | int | str]] = []
    country = np.repeat(np.arange(countries), cities // countries)
    for persistence in persistence_values:
        if not 0 <= persistence < 1:
            raise SourceSchemaError("Simulation persistence must be in [0, 1)")
        for panel_length in panel_lengths:
            for replication in range(replications):
                city_effect = rng.normal(0, 0.35, cities)
                state = city_effect / (1 - persistence) + rng.normal(0, 0.3, cities)
                rows = []
                # Burn-in reduces dependence on an arbitrary initial condition.
                for time in range(30 + panel_length):
                    country_shock = rng.normal(0, 0.08, countries)
                    covariate = rng.normal(size=cities)
                    outcome = (
                        persistence * state + 0.3 * covariate + city_effect
                        + country_shock[country] + rng.normal(0, 0.25, cities)
                    )
                    if time >= 30:
                        for index in range(cities):
                            rows.append(
                                {
                                    "city_id": index,
                                    "country_code": country[index],
                                    "period": time - 30,
                                    "growth": outcome[index],
                                    "lagged_growth": state[index],
                                    "x": covariate[index],
                                }
                            )
                    state = outcome
                sample = common_dynamic_sample(
                    pd.DataFrame(rows), outcome="growth", lagged_outcome="lagged_growth",
                    covariates=["x"],
                )
                estimates = fit_dynamic_hierarchy(
                    sample, outcome="growth", lagged_outcome="lagged_growth", covariates=["x"]
                )
                for row in estimates.loc[estimates["term"].eq("lagged_growth")].itertuples():
                    records.append(
                        {
                            "persistence": persistence,
                            "panel_length": panel_length,
                            "replication": replication,
                            "estimator_id": row.estimator_id,
                            "estimate": row.estimate,
                            "error": row.estimate - persistence,
                        }
                    )
    raw = pd.DataFrame(records)
    summary = raw.groupby(
        ["persistence", "panel_length", "estimator_id"], as_index=False
    ).agg(mean_estimate=("estimate", "mean"), bias=("error", "mean"), rmse=(
        "error", lambda values: float(np.sqrt(np.mean(np.square(values))))
    ))
    summary["replications"] = replications
    summary["cities"] = cities
    summary["seed"] = seed
    return summary
