"""Contracts for leakage-resistant Mexico locality concordance chains."""

from __future__ import annotations

import numpy as np
import pandas as pd

from urban_growth.io import SourceSchemaError, reject_duplicate_keys, require_columns

ACCEPTED_MATCH_STATUS = {
    "stable_geometry",
    "official_crosswalk",
    "harmonized_common_geography",
}
ALLOWED_EVENT_TYPES = {"census", "population_count"}


def validate_mexico_locality_transition(transition: pd.DataFrame) -> pd.DataFrame:
    """Validate one locality transition without borrowing future geography."""
    required = {
        "analysis_id",
        "origin_year",
        "endpoint_year",
        "origin_population",
        "endpoint_population",
        "origin_event_type",
        "endpoint_event_type",
        "match_status",
        "relationship_cardinality",
        "origin_overlap_ratio",
        "endpoint_overlap_ratio",
        "official_relationship_verified",
        "all_components_identified",
        "population_aggregation_complete",
        "double_count_free",
        "methodology_comparable",
        "evidence_reference_year",
        "uses_future_boundary_reference",
        "exclusion_reason",
    }
    require_columns(transition, required, source_name="Mexico locality transition")
    reject_duplicate_keys(
        transition,
        ["analysis_id", "origin_year", "endpoint_year"],
        source_name="Mexico locality transition",
    )
    out = transition.copy()
    if (out["endpoint_year"] <= out["origin_year"]).any():
        raise SourceSchemaError("Mexico transition endpoint must follow origin year")
    if not out["origin_event_type"].isin(ALLOWED_EVENT_TYPES).all():
        raise SourceSchemaError("Mexico transition has unsupported origin event type")
    if not out["endpoint_event_type"].isin(ALLOWED_EVENT_TYPES).all():
        raise SourceSchemaError("Mexico transition has unsupported endpoint event type")
    for column in ("origin_population", "endpoint_population"):
        numeric = pd.to_numeric(out[column], errors="coerce")
        if numeric.isna().any() or numeric.le(0).any():
            raise SourceSchemaError(f"{column} must contain positive direct counts")
    evidence_year = pd.to_numeric(out["evidence_reference_year"], errors="coerce")
    if evidence_year.isna().any() or (evidence_year > out["endpoint_year"]).any():
        raise SourceSchemaError(
            "Mexico concordance evidence may not post-date its transition endpoint"
        )
    if out["uses_future_boundary_reference"].fillna(False).astype(bool).any():
        raise SourceSchemaError(
            "Mexico concordance may not use a boundary reference after the transition"
        )

    accepted = out["match_status"].isin(ACCEPTED_MATCH_STATUS)
    one_to_one = out["relationship_cardinality"].eq("one_to_one")
    harmonized = out["match_status"].eq("harmonized_common_geography")
    geometry_pass = (
        pd.to_numeric(out["origin_overlap_ratio"], errors="coerce").ge(0.995)
        & pd.to_numeric(out["endpoint_overlap_ratio"], errors="coerce").ge(0.995)
    )
    official = out["official_relationship_verified"].fillna(False).astype(bool)
    components = out["all_components_identified"].fillna(False).astype(bool)
    aggregation = out["population_aggregation_complete"].fillna(False).astype(bool)
    no_double_count = out["double_count_free"].fillna(False).astype(bool)
    methodology = out["methodology_comparable"].fillna(False).astype(bool)

    invalid_one_to_one = accepted & ~harmonized & (~one_to_one | ~official | ~geometry_pass)
    if invalid_one_to_one.any():
        raise SourceSchemaError(
            "Accepted Mexico one-to-one matches require official relationship and 99.5% overlap"
        )
    invalid_harmonized = harmonized & (
        ~official | ~components | ~aggregation | ~no_double_count | ~geometry_pass
    )
    if invalid_harmonized.any():
        raise SourceSchemaError(
            "Harmonized Mexico matches require complete official components, aggregation, "
            "no double counting, and 99.5% union overlap"
        )

    out["transition_eligible"] = accepted & methodology
    out["transition_exclusion_reason"] = out["exclusion_reason"].fillna("").astype(str)
    out.loc[accepted & ~methodology, "transition_exclusion_reason"] = (
        "methodology_not_comparable"
    )
    unresolved_without_reason = ~accepted & out["transition_exclusion_reason"].eq("")
    out.loc[unresolved_without_reason, "transition_exclusion_reason"] = (
        "unresolved_concordance"
    )
    return out


def build_mexico_multiwave_history(transitions: pd.DataFrame) -> pd.DataFrame:
    """Build adjacent-transition forecast rows without future-boundary leakage.

    A forecast row is eligible only when both its outcome transition and the immediately
    preceding transition used for recent growth pass independently. Later geography cannot
    repair an earlier predictor interval.
    """
    checked = validate_mexico_locality_transition(transitions)
    checked = checked.sort_values(["analysis_id", "origin_year", "endpoint_year"]).copy()
    duration = checked["endpoint_year"] - checked["origin_year"]
    checked["interval_log_growth"] = (
        np.log(pd.to_numeric(checked["endpoint_population"]))
        - np.log(pd.to_numeric(checked["origin_population"]))
    ) / duration

    previous = checked[
        [
            "analysis_id",
            "origin_year",
            "endpoint_year",
            "interval_log_growth",
            "transition_eligible",
        ]
    ].rename(
        columns={
            "origin_year": "previous_origin_year",
            "endpoint_year": "origin_year",
            "interval_log_growth": "recent_growth",
            "transition_eligible": "history_transition_eligible",
        }
    )
    current = checked.merge(
        previous,
        on=["analysis_id", "origin_year"],
        how="left",
        validate="one_to_one",
    )
    current["forecast_interval_eligible"] = (
        current["transition_eligible"]
        & current["history_transition_eligible"].fillna(False).astype(bool)
        & current["previous_origin_year"].notna()
    )
    current["future_growth"] = current["interval_log_growth"]
    current["period_start"] = current["origin_year"]
    current["period_end"] = current["endpoint_year"]
    current["country_code"] = "MEX"
    current["city_id"] = current["analysis_id"].astype(str)
    current["growth_eligible"] = current["forecast_interval_eligible"]
    current["headline_eligible"] = current["forecast_interval_eligible"]
    current["boundary_history_uses_future_reference"] = False
    current["forecast_deployable_at_origin"] = current["forecast_interval_eligible"]
    return current


def mexico_transition_coverage(
    transition: pd.DataFrame,
    *,
    cohort_min: int = 25_000,
    cohort_max: int = 100_000,
) -> pd.DataFrame:
    """Report count- and population-weighted coverage before dropping exclusions."""
    checked = validate_mexico_locality_transition(transition)
    cohort = checked.loc[
        pd.to_numeric(checked["origin_population"]).between(cohort_min, cohort_max)
    ].copy()
    if cohort.empty:
        raise SourceSchemaError("Mexico transition has no registered threshold cohort")
    rows = []
    for (origin_year, endpoint_year), group in cohort.groupby(["origin_year", "endpoint_year"]):
        eligible = group["transition_eligible"]
        population = pd.to_numeric(group["origin_population"])
        eligible_population = population.loc[eligible].sum()
        rows.append(
            {
                "origin_year": int(origin_year),
                "endpoint_year": int(endpoint_year),
                "origin_localities": len(group),
                "eligible_localities": int(eligible.sum()),
                "count_coverage": float(eligible.mean()),
                "origin_population": float(population.sum()),
                "eligible_origin_population": float(eligible_population),
                "population_coverage": float(eligible_population / population.sum()),
            }
        )
    return pd.DataFrame(rows).sort_values(["origin_year", "endpoint_year"]).reset_index(drop=True)
