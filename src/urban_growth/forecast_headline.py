"""Headline-qualified persistence evaluation with origin risk-set coverage enforcement."""
# ruff: noqa: I001

from __future__ import annotations

import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns


COVERAGE_COLUMNS = {
    "origin",
    "origin_risk_set_rows",
    "observed_outcome_rows",
    "missing_outcome_rows",
    "observed_outcome_share",
    "coverage_denominator_rule",
    "future_outcome_used_for_membership",
}


def _validate_origin_coverage(
    coverage_summary: pd.DataFrame,
    origins: list[int],
) -> pd.DataFrame:
    """Validate an origin-defined outcome-coverage denominator before headline use."""
    require_columns(
        coverage_summary,
        COVERAGE_COLUMNS,
        source_name="headline forecast coverage summary",
    )
    reject_duplicate_keys(
        coverage_summary,
        ["origin"],
        source_name="headline forecast coverage summary",
    )
    if not origins or len(set(origins)) != len(origins):
        raise SourceSchemaError("Headline forecast origins must be unique and non-empty")

    coverage = coverage_summary.copy()
    declared = sorted(origins)
    available = set(coverage["origin"])
    missing = [origin for origin in declared if origin not in available]
    if missing:
        raise SourceSchemaError(f"Origin risk-set coverage is missing declared origins: {missing}")
    coverage = coverage.loc[coverage["origin"].isin(declared)].copy()

    risk = pd.to_numeric(coverage["origin_risk_set_rows"], errors="coerce")
    observed = pd.to_numeric(coverage["observed_outcome_rows"], errors="coerce")
    missing_rows = pd.to_numeric(coverage["missing_outcome_rows"], errors="coerce")
    share = pd.to_numeric(coverage["observed_outcome_share"], errors="coerce")
    if risk.isna().any() or risk.le(0).any():
        raise SourceSchemaError("origin_risk_set_rows must be positive and known")
    if observed.isna().any() or observed.lt(0).any() or observed.gt(risk).any():
        raise SourceSchemaError("observed_outcome_rows must be between zero and the origin risk set")
    if missing_rows.isna().any() or missing_rows.lt(0).any():
        raise SourceSchemaError("missing_outcome_rows must be non-negative and known")
    if not (observed + missing_rows).eq(risk).all():
        raise SourceSchemaError("Observed plus missing outcome rows must equal the origin risk set")
    expected_share = observed / risk
    if share.isna().any() or share.sub(expected_share).abs().gt(1e-12).any():
        raise SourceSchemaError("observed_outcome_share disagrees with the coverage counts")
    if coverage["coverage_denominator_rule"].ne("lag_and_origin_predictors_only").any():
        raise SourceSchemaError("Headline coverage denominator must use lag/origin predictors only")
    future_membership = coverage["future_outcome_used_for_membership"]
    if not pd.api.types.is_bool_dtype(future_membership.dtype):
        raise SourceSchemaError("future_outcome_used_for_membership must be boolean")
    if future_membership.any():
        raise SourceSchemaError("Future outcome observability cannot define headline risk-set membership")

    return coverage.sort_values("origin").reset_index(drop=True)


def _headline_coverage(
    coverage_summary: pd.DataFrame,
    origins: list[int],
    *,
    coverage_policy_id: str,
) -> pd.DataFrame:
    from urban_growth.coverage_policy import resolve_registered_coverage_policy

    coverage = _validate_origin_coverage(coverage_summary, origins)
    policy = resolve_registered_coverage_policy(coverage_policy_id)
    minimum = float(policy.minimum_observed_outcome_share)

    result = coverage.copy()
    result["coverage_policy_id"] = policy.policy_id
    result["minimum_observed_outcome_share"] = minimum
    result["coverage_policy_reference"] = str(policy.reference).strip()
    result["coverage_policy_registry_enforced"] = True
    result["coverage_policy_passed"] = result["observed_outcome_share"].ge(minimum)
    failed = result.loc[~result["coverage_policy_passed"], "origin"].tolist()
    if failed:
        raise SourceSchemaError(
            "Observed-outcome coverage is below the registered headline minimum for origins: "
            f"{failed}"
        )
    return result


def _attach_coverage_to_metrics(
    metrics: pd.DataFrame,
    coverage: pd.DataFrame,
) -> pd.DataFrame:
    result = metrics.merge(coverage, on="origin", how="left", validate="many_to_one")
    required_attached = COVERAGE_COLUMNS - {"origin"}
    if result[list(required_attached)].isna().any().any():
        raise SourceSchemaError("Persistence metrics could not be matched to origin risk-set coverage")
    max_scored = result.groupby("origin")["n"].max()
    observed = coverage.set_index("origin")["observed_outcome_rows"]
    if (max_scored > observed.reindex(max_scored.index)).any():
        raise SourceSchemaError("Scored persistence rows exceed observed outcomes in the origin risk set")
    result["origin_risk_set_coverage_enforced"] = True
    result["headline_coverage_contract_enforced"] = True
    result["headline_coverage_minimum_enforced"] = True
    result["benchmark_stage"] = "point_in_time_persistence_with_origin_coverage"
    return result.sort_values(["origin", "model"]).reset_index(drop=True)


def evaluate_headline_point_in_time_persistence(
    panel: pd.DataFrame,
    origins: list[int],
    coverage_summary: pd.DataFrame,
    *,
    coverage_policy_id: str,
    **kwargs: object,
) -> pd.DataFrame:
    """Evaluate point-in-time persistence only under a versioned coverage policy."""
    from urban_growth.forecast_fitness import evaluate_point_in_time_persistence_baselines

    coverage = _headline_coverage(
        coverage_summary,
        origins,
        coverage_policy_id=coverage_policy_id,
    )
    metrics = evaluate_point_in_time_persistence_baselines(panel, origins, **kwargs)
    return _attach_coverage_to_metrics(metrics, coverage)


def headline_point_in_time_persistence_errors(
    panel: pd.DataFrame,
    origins: list[int],
    coverage_summary: pd.DataFrame,
    *,
    coverage_policy_id: str,
    **kwargs: object,
) -> pd.DataFrame:
    """Return row-level errors only under a versioned coverage policy."""
    from urban_growth.forecast_fitness import point_in_time_persistence_errors

    coverage = _headline_coverage(
        coverage_summary,
        origins,
        coverage_policy_id=coverage_policy_id,
    )
    errors = point_in_time_persistence_errors(panel, origins, **kwargs)
    result = errors.merge(coverage, on="origin", how="left", validate="many_to_one")
    required_attached = COVERAGE_COLUMNS - {"origin"}
    if result[list(required_attached)].isna().any().any():
        raise SourceSchemaError("Persistence errors could not be matched to origin risk-set coverage")
    scored = result.groupby(["origin", "model"])["city_id"].nunique()
    observed = coverage.set_index("origin")["observed_outcome_rows"]
    for (origin, _model), count in scored.items():
        if count > observed.loc[origin]:
            raise SourceSchemaError(
                "Scored persistence error rows exceed observed outcomes in the origin risk set"
            )
    result["origin_risk_set_coverage_enforced"] = True
    result["headline_coverage_contract_enforced"] = True
    result["headline_coverage_minimum_enforced"] = True
    result["benchmark_stage"] = "point_in_time_persistence_with_origin_coverage"
    return result.reset_index(drop=True)
