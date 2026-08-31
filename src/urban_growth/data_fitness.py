from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

ACCEPTED_CONCORDANCE = {
    "stable",
    "official_crosswalk",
    "harmonized_common_geography",
}

PASS_VALIDATION = {"passed"}
BAD_EXPOSURE = {"material", "unknown"}
UNRESOLVED_BOUNDARY = {
    "annexation",
    "merger",
    "split",
    "reclassification",
    "unresolved",
    "unknown",
}


def _norm(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return _norm(value) in {"1", "true", "yes", "y", "passed", "valid"}


def _join_reasons(reasons: Iterable[str]) -> str:
    return ";".join(sorted(set(reasons)))


def _evaluate_row(row: pd.Series) -> dict[str, object]:
    level_reasons: list[str] = []
    growth_reasons: list[str] = []
    spatial_reasons: list[str] = []
    headline_reasons: list[str] = []

    source_id = _norm(row.get("source_id"))
    population_concept = _norm(row.get("population_concept"))
    geographic_unit = _norm(row.get("geographic_unit"))
    validation_status = _norm(row.get("validation_status"))
    concordance_status = _norm(row.get("concordance_status"))
    boundary_change_status = _norm(row.get("boundary_change_status"))
    truncation_exposure = _norm(row.get("truncation_exposure"))
    survivorship_exposure = _norm(row.get("survivorship_exposure"))

    if not source_id:
        level_reasons.append("missing_source_id")
        growth_reasons.append("missing_source_id")
        spatial_reasons.append("missing_source_id")

    if not population_concept:
        level_reasons.append("missing_population_concept")
        growth_reasons.append("missing_population_concept")

    if not geographic_unit:
        level_reasons.append("missing_geographic_unit")
        growth_reasons.append("missing_geographic_unit")
        spatial_reasons.append("missing_geographic_unit")

    if validation_status not in PASS_VALIDATION:
        level_reasons.append("validation_not_passed")
        growth_reasons.append("validation_not_passed")
        spatial_reasons.append("validation_not_passed")

    geographic_comparable = _truthy(row.get("geographic_comparable"))
    temporal_comparable = _truthy(row.get("temporal_comparable"))
    boundary_fixed = _truthy(row.get("boundary_temporally_fixed"))
    harmonized = concordance_status == "harmonized_common_geography"

    if not geographic_comparable:
        level_reasons.append("geography_not_comparable")

    if not temporal_comparable:
        growth_reasons.append("time_not_comparable")

    if concordance_status not in ACCEPTED_CONCORDANCE:
        growth_reasons.append("concordance_not_accepted")
        spatial_reasons.append("concordance_not_accepted")

    if not boundary_fixed and not harmonized:
        growth_reasons.append("boundary_not_stable_or_harmonized")

    if boundary_change_status in UNRESOLVED_BOUNDARY and not harmonized:
        growth_reasons.append("unresolved_boundary_change")

    if _truthy(row.get("administrative_reclassification")) and not harmonized:
        growth_reasons.append("administrative_reclassification")

    if _truthy(row.get("methodology_change")):
        growth_reasons.append("methodology_change")

    if _truthy(row.get("known_inconsistency")):
        level_reasons.append("known_inconsistency")
        growth_reasons.append("known_inconsistency")
        spatial_reasons.append("known_inconsistency")

    if not _truthy(row.get("coordinates_validated")):
        spatial_reasons.append("coordinates_not_validated")

    if not _truthy(row.get("network_geography_validated")):
        spatial_reasons.append("network_geography_not_validated")

    level_eligible = not level_reasons
    growth_eligible = not growth_reasons
    spatial_eligible = not spatial_reasons

    if not growth_eligible:
        headline_reasons.append("not_growth_eligible")
    if validation_status not in PASS_VALIDATION:
        headline_reasons.append("validation_not_passed")
    if concordance_status not in ACCEPTED_CONCORDANCE:
        headline_reasons.append("concordance_not_accepted")
    if boundary_change_status in UNRESOLVED_BOUNDARY and not harmonized:
        headline_reasons.append("unresolved_boundary_change")
    if truncation_exposure in BAD_EXPOSURE:
        headline_reasons.append("truncation_exposure")
    if survivorship_exposure in BAD_EXPOSURE:
        headline_reasons.append("survivorship_exposure")
    if _truthy(row.get("known_inconsistency")):
        headline_reasons.append("known_inconsistency")

    headline_eligible = not headline_reasons

    all_reasons = level_reasons + growth_reasons + spatial_reasons + headline_reasons

    return {
        "level_eligible": level_eligible,
        "level_exclusion_reasons": _join_reasons(level_reasons),
        "growth_eligible": growth_eligible,
        "growth_exclusion_reasons": _join_reasons(growth_reasons),
        "spatial_eligible": spatial_eligible,
        "spatial_exclusion_reasons": _join_reasons(spatial_reasons),
        "headline_eligible": headline_eligible,
        "headline_exclusion_reasons": _join_reasons(headline_reasons),
        "fitness_reasons": _join_reasons(all_reasons),
    }


def evaluate_city_data_fitness(frame: pd.DataFrame) -> pd.DataFrame:
    """Return *frame* with deterministic analysis-specific fitness flags appended.

    The function never edits source values and never computes a composite quality score.
    Missing evidence fails only the analytical dimensions that require that evidence.
    """
    out = frame.copy()
    if out.empty:
        for column in (
            "level_eligible",
            "level_exclusion_reasons",
            "growth_eligible",
            "growth_exclusion_reasons",
            "spatial_eligible",
            "spatial_exclusion_reasons",
            "headline_eligible",
            "headline_exclusion_reasons",
            "fitness_reasons",
        ):
            out[column] = pd.Series(dtype="bool" if column.endswith("eligible") else "object")
        return out

    evaluated = pd.DataFrame((_evaluate_row(row) for _, row in out.iterrows()), index=out.index)
    return pd.concat([out, evaluated], axis=1)


def headline_sample(frame: pd.DataFrame) -> pd.DataFrame:
    """Evaluate fitness and return only records permitted in headline analyses."""
    evaluated = evaluate_city_data_fitness(frame)
    return evaluated.loc[evaluated["headline_eligible"]].copy()
