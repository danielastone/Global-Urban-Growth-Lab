"""Locked estimator hierarchy for dynamic city-growth panels."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

EXPECTED_COVERAGE_PERSISTENCE = {0.2, 0.6, 0.9}
EXPECTED_COVERAGE_LENGTHS = {6, 8, 10}
EXPECTED_COVERAGE_ESTIMATORS = {
    "pooled_dynamic", "city_fe_dynamic", "half_panel_jackknife"
}


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
    weights: np.ndarray | None = None,
) -> pd.DataFrame:
    y, x, names = _design(
        sample, outcome=outcome, lagged_outcome=lagged_outcome, covariates=covariates,
        city=city, city_fixed_effects=city_fixed_effects,
    )
    if weights is None:
        fit_x, fit_y = x, y
    else:
        weights = np.asarray(weights, dtype=float)
        if len(weights) != len(sample) or not np.isfinite(weights).all() or (weights <= 0).any():
            raise SourceSchemaError("Estimator weights must be finite, positive, and row-aligned")
        root_weight = np.sqrt(weights)
        fit_x, fit_y = x * root_weight[:, None], y * root_weight
    beta = np.linalg.lstsq(fit_x, fit_y, rcond=None)[0]
    residual = y - x @ beta
    target_count = 1 + len(covariates)
    if weights is None:
        bread = np.linalg.pinv(x.T @ x)
        country_meat = _cluster_meat(x, residual, sample[country])
        period_meat = _cluster_meat(x, residual, sample[period])
        intersection = sample[country].astype(str) + "::" + sample[period].astype(str)
        covariance = bread @ (
            country_meat + period_meat - _cluster_meat(x, residual, intersection)
        ) @ bread
        standard_errors = np.sqrt(np.maximum(np.diag(covariance)[:target_count], 0.0))
    else:
        standard_errors = np.repeat(np.nan, target_count)
    return pd.DataFrame(
        {
            "term": names[:target_count],
            "estimate": beta[:target_count],
            "std_error_country_period": standard_errors,
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
    weights: np.ndarray | None = None,
) -> pd.DataFrame:
    """Fit pooled, city-FE, and split-panel-jackknife estimates on one full sample."""
    required = {outcome, lagged_outcome, city, country, period, "country_period", *covariates}
    require_columns(sample, required, source_name="dynamic common sample")
    pooled = _fit_ols(
        sample, outcome=outcome, lagged_outcome=lagged_outcome, covariates=covariates,
        city=city, country=country, period=period, city_fixed_effects=False, weights=weights,
    ).assign(estimator_id="pooled_dynamic")
    fixed = _fit_ols(
        sample, outcome=outcome, lagged_outcome=lagged_outcome, covariates=covariates,
        city=city, country=country, period=period, city_fixed_effects=True, weights=weights,
    ).assign(estimator_id="city_fe_dynamic")
    periods = sorted(sample[period].unique())
    if len(periods) < 4:
        raise SourceSchemaError("Half-panel jackknife requires at least four periods")
    midpoint = len(periods) // 2
    halves = [periods[:midpoint], periods[midpoint:]]
    half_estimates = []
    for half in halves:
        half_mask = sample[period].isin(half).to_numpy()
        half_sample = sample.loc[half_mask].copy()
        if half_sample.groupby(city)[city].size().min() < 2:
            raise SourceSchemaError("Each jackknife half requires two observations per city")
        half_estimates.append(
            _fit_ols(
                half_sample, outcome=outcome, lagged_outcome=lagged_outcome,
                covariates=covariates, city=city, country=country, period=period,
                city_fixed_effects=True,
                weights=None if weights is None else np.asarray(weights)[half_mask],
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


def bootstrap_dynamic_hierarchy(
    sample: pd.DataFrame,
    *,
    outcome: str,
    lagged_outcome: str,
    covariates: list[str],
    city: str = "city_id",
    country: str = "country_code",
    period: str = "period",
    replications: int = 999,
    confidence_level: float = 0.95,
    seed: int = 2718,
) -> pd.DataFrame:
    """Infer uncertainty using country-by-period product multiplier weights.

    Positive exponential multipliers preserve every city's ordered history and the fixed-effect
    design while perturbing the two declared dependence dimensions independently. Runs below
    399 replications are allowed for tests but are marked non-production.
    """
    if replications < 20:
        raise SourceSchemaError("Dynamic bootstrap requires at least 20 replications")
    if not 0.5 < confidence_level < 1:
        raise SourceSchemaError("Bootstrap confidence_level must be between 0.5 and 1")
    required = {outcome, lagged_outcome, city, country, period, "country_period", *covariates}
    require_columns(sample, required, source_name="dynamic bootstrap sample")
    countries = pd.Index(sample[country].drop_duplicates())
    periods = pd.Index(sample[period].drop_duplicates())
    if len(countries) < 2 or len(periods) < 4:
        raise SourceSchemaError("Dynamic bootstrap requires two countries and four periods")
    point = fit_dynamic_hierarchy(
        sample, outcome=outcome, lagged_outcome=lagged_outcome, covariates=covariates,
        city=city, country=country, period=period,
    )[["estimator_id", "term", "estimate"]]
    rng = np.random.default_rng(seed)
    draws = []
    for replication in range(replications):
        country_weights = pd.Series(rng.exponential(size=len(countries)), index=countries)
        period_weights = pd.Series(rng.exponential(size=len(periods)), index=periods)
        country_weights /= country_weights.mean()
        period_weights /= period_weights.mean()
        row_weights = (
            sample[country].map(country_weights).to_numpy()
            * sample[period].map(period_weights).to_numpy()
        )
        estimate = fit_dynamic_hierarchy(
            sample, outcome=outcome, lagged_outcome=lagged_outcome, covariates=covariates,
            city=city, country=country, period=period, weights=row_weights,
        )[["estimator_id", "term", "estimate"]]
        estimate["replication"] = replication
        draws.append(estimate)
    draw_frame = pd.concat(draws, ignore_index=True)
    alpha = (1 - confidence_level) / 2
    summary = draw_frame.groupby(["estimator_id", "term"], as_index=False).agg(
        bootstrap_std_error=("estimate", "std"),
        confidence_lower=("estimate", lambda values: values.quantile(alpha)),
        confidence_upper=("estimate", lambda values: values.quantile(1 - alpha)),
    )
    result = point.rename(columns={"estimate": "point_estimate"}).merge(
        summary, on=["estimator_id", "term"], validate="one_to_one"
    )
    result["bootstrap_method"] = "country-period product exponential multiplier"
    result["confidence_level"] = confidence_level
    result["replications"] = replications
    result["seed"] = seed
    result["production_replications"] = replications >= 399
    return result


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


def _simulate_dynamic_panel(
    rng: np.random.Generator,
    *,
    persistence: float,
    panel_length: int,
    cities: int,
    countries: int,
) -> pd.DataFrame:
    country = np.repeat(np.arange(countries), cities // countries)
    city_effect = rng.normal(0, 0.35, cities)
    state = city_effect / (1 - persistence) + rng.normal(0, 0.3, cities)
    rows = []
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
    return pd.DataFrame(rows)


def _validate_simulation_design(
    persistence_values: tuple[float, ...],
    panel_lengths: tuple[int, ...],
    cities: int,
    countries: int,
) -> None:
    if cities % countries or cities // countries < 2:
        raise SourceSchemaError("Simulation requires at least two equal-count cities per country")
    if min(panel_lengths) < 4:
        raise SourceSchemaError("Simulation requires at least four panel periods")
    if any(not 0 <= persistence < 1 for persistence in persistence_values):
        raise SourceSchemaError("Simulation persistence must be in [0, 1)")


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
    _validate_simulation_design(persistence_values, panel_lengths, cities, countries)
    if replications < 2:
        raise SourceSchemaError("Simulation requires at least two replications")
    rng = np.random.default_rng(seed)
    records: list[dict[str, float | int | str]] = []
    for persistence in persistence_values:
        for panel_length in panel_lengths:
            for replication in range(replications):
                panel = _simulate_dynamic_panel(
                    rng, persistence=persistence, panel_length=panel_length,
                    cities=cities, countries=countries,
                )
                sample = common_dynamic_sample(
                    panel, outcome="growth", lagged_outcome="lagged_growth",
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


def _wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> tuple[float, float]:
    rate = successes / trials
    denominator = 1 + z**2 / trials
    center = (rate + z**2 / (2 * trials)) / denominator
    margin = z * np.sqrt(rate * (1 - rate) / trials + z**2 / (4 * trials**2)) / denominator
    return center - margin, center + margin


def _apply_coverage_gate(summary: pd.DataFrame, *, production: bool) -> pd.DataFrame:
    result = summary.copy()
    adequate = result["coverage_wilson_lower"].ge(0.90) & result[
        "coverage_wilson_upper"
    ].le(0.99)
    eligible = result["estimator_id"].eq("half_panel_jackknife") & production
    result["production_design"] = production
    result["coverage_gate_eligible"] = eligible
    result["coverage_gate_pass"] = pd.array(
        adequate.where(eligible, pd.NA), dtype="boolean"
    )
    return result


def simulate_bootstrap_coverage(
    *,
    persistence_values: tuple[float, ...] = (0.2, 0.6, 0.9),
    panel_lengths: tuple[int, ...] = (6, 8, 10),
    simulation_replications: int = 200,
    bootstrap_replications: int = 399,
    cities: int = 48,
    countries: int = 6,
    confidence_level: float = 0.95,
    seed: int = 314159,
) -> pd.DataFrame:
    """Estimate interval coverage and apply the predeclared production gate.

    A design cell is production-eligible only with at least 200 simulated panels and 399
    bootstrap draws. Its Wilson interval for empirical coverage must lie wholly inside the
    predeclared 0.90--0.99 adequacy band. This rejects both undercoverage and vacuous intervals.
    """
    _validate_simulation_design(persistence_values, panel_lengths, cities, countries)
    if simulation_replications < 2:
        raise SourceSchemaError("Coverage simulation requires at least two panels per cell")
    if bootstrap_replications < 20:
        raise SourceSchemaError("Coverage simulation requires at least 20 bootstrap draws")
    rng = np.random.default_rng(seed)
    records = []
    for persistence in persistence_values:
        for panel_length in panel_lengths:
            for replication in range(simulation_replications):
                panel = _simulate_dynamic_panel(
                    rng, persistence=persistence, panel_length=panel_length,
                    cities=cities, countries=countries,
                )
                sample = common_dynamic_sample(
                    panel, outcome="growth", lagged_outcome="lagged_growth", covariates=["x"]
                )
                bootstrap_seed = int(rng.integers(0, np.iinfo(np.int32).max))
                intervals = bootstrap_dynamic_hierarchy(
                    sample, outcome="growth", lagged_outcome="lagged_growth", covariates=["x"],
                    replications=bootstrap_replications, confidence_level=confidence_level,
                    seed=bootstrap_seed,
                )
                intervals = intervals.loc[intervals["term"].eq("lagged_growth")]
                for row in intervals.itertuples():
                    records.append(
                        {
                            "persistence": persistence,
                            "panel_length": panel_length,
                            "simulation_replication": replication,
                            "estimator_id": row.estimator_id,
                            "covered": row.confidence_lower <= persistence <= row.confidence_upper,
                            "interval_width": row.confidence_upper - row.confidence_lower,
                        }
                    )
    raw = pd.DataFrame(records)
    grouped = raw.groupby(["persistence", "panel_length", "estimator_id"], as_index=False)
    summary = grouped.agg(
        covered_panels=("covered", "sum"),
        evaluated_panels=("covered", "size"),
        empirical_coverage=("covered", "mean"),
        median_interval_width=("interval_width", "median"),
    )
    wilson = summary.apply(
        lambda row: _wilson_interval(int(row["covered_panels"]), int(row["evaluated_panels"])),
        axis=1,
    )
    summary[["coverage_wilson_lower", "coverage_wilson_upper"]] = pd.DataFrame(
        wilson.tolist(), index=summary.index
    )
    production = simulation_replications >= 200 and bootstrap_replications >= 399
    summary = _apply_coverage_gate(summary, production=production)
    summary["nominal_confidence"] = confidence_level
    summary["simulation_replications"] = simulation_replications
    summary["bootstrap_replications"] = bootstrap_replications
    summary["cities"] = cities
    summary["countries"] = countries
    summary["seed"] = seed
    return summary


def combine_coverage_artifacts(input_dir: Path) -> pd.DataFrame:
    """Return one validated production grid from nine cell files."""
    paths = sorted(input_dir.rglob("dynamic_bootstrap_coverage_*.csv"))
    if len(paths) != 9:
        raise SourceSchemaError(f"Expected nine coverage artifacts, found {len(paths)}")
    result = pd.concat([pd.read_csv(path) for path in paths], ignore_index=True)
    required = {
        "persistence", "panel_length", "estimator_id", "production_design",
        "coverage_gate_eligible", "coverage_gate_pass",
    }
    require_columns(result, required, source_name="bootstrap coverage artifacts")
    for column in ("production_design", "coverage_gate_eligible", "coverage_gate_pass"):
        result[column] = result[column].map(
            {True: True, False: False, "True": True, "False": False}
        ).astype("boolean")
    if set(result["persistence"]) != EXPECTED_COVERAGE_PERSISTENCE:
        raise SourceSchemaError("Coverage artifacts do not span the locked persistence grid")
    if set(result["panel_length"]) != EXPECTED_COVERAGE_LENGTHS:
        raise SourceSchemaError("Coverage artifacts do not span the locked panel-length grid")
    if set(result["estimator_id"]) != EXPECTED_COVERAGE_ESTIMATORS:
        raise SourceSchemaError("Coverage artifacts do not span the implemented estimators")
    keys = ["persistence", "panel_length", "estimator_id"]
    if len(result) != 27 or result.duplicated(keys).any():
        raise SourceSchemaError("Coverage artifacts must contain 27 unique design-estimator rows")
    if not result["production_design"].all():
        raise SourceSchemaError("At least one coverage artifact is not a production design")
    eligible = result["estimator_id"].eq("half_panel_jackknife")
    if not result.loc[eligible, "coverage_gate_eligible"].all():
        raise SourceSchemaError("Every corrected-estimator cell must be gate eligible")
    if result.loc[~eligible, "coverage_gate_eligible"].any():
        raise SourceSchemaError("Diagnostic estimators cannot receive a structural coverage gate")
    return result.sort_values(keys).reset_index(drop=True)


def check_coverage_gate(result: pd.DataFrame) -> None:
    """Raise unless all nine eligible corrected-estimator cells pass."""
    require_columns(
        result,
        {"persistence", "panel_length", "estimator_id", "coverage_gate_eligible",
         "coverage_gate_pass"},
        source_name="combined bootstrap coverage",
    )
    eligible = result.loc[result["coverage_gate_eligible"]]
    if len(eligible) != 9:
        raise SourceSchemaError("Expected nine eligible corrected-estimator cells")
    failed = eligible.loc[~eligible["coverage_gate_pass"].astype("boolean").fillna(False)]
    if not failed.empty:
        cells = ", ".join(
            f"rho={row.persistence}, T={row.panel_length}" for row in failed.itertuples()
        )
        raise SourceSchemaError(f"Bootstrap coverage gate failed: {cells}")
