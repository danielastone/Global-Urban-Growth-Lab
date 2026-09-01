from __future__ import annotations

from collections.abc import Iterable

import pandas as pd

ACCEPTED_CONCORDANCE = {
    "stable",
    "official_crosswalk",
    "harmonized_common_geography",
}

PASS_VALIDATION = {"passed"}
ACCEPTED_EXPOSURE = {"none", "low", "material", "unknown"}
BAD_EXPOSURE = {"material", "unknown"}
UNKNOWN_EVIDENCE = {"unknown", "uncertain", "unresolved", "not_reviewed", "not reviewed"}
PRESENT_EVIDENCE = {"1", "true", "yes", "y", "passed", "valid", "present"}
CLEAR_EVIDENCE = {"0", "false", "no", "n", "clear", "none", "absent"}
CLEAR_BOUNDARY_STATUS = {
    "none",
    "stable",
    "unchanged",
    "harmonized",
    "official_crosswalk",
    "none_within_fixed_2025_footprint",
}
UNRESOLVED_BOUNDARY = {
    "annexation",
    "merger",
    "split",
    "reclassification",
    "unresolved",
    "unknown",
}
FITNESS_OUTPUT_COLUMNS = (
    "level_eligible",
    "level_exclusion_reasons",
    "growth_eligible",
    "growth_exclusion_reasons",
    "spatial_eligible",
    "spatial_exclusion_reasons",
    "headline_eligible",
    "headline_exclusion_reasons",
    "fitness_reasons",
)


def _norm(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def _truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return _norm(value) in PRESENT_EVIDENCE


def _negative_evidence_state(value: object) -> str:
    """Return clear / present / unknown for evidence asserting an adverse condition.

    These fields answer questions such as whether a methodology changed or a known
    inconsistency exists. Only explicit clear/present values are accepted. Missing,
    uncertain, or unrecognized values remain unknown so lack of evidence cannot be
    interpreted as evidence that the adverse condition is absent.
    """
    if isinstance(value, bool):
        return "present" if value else "clear"
    normalized = _norm(value)
    if normalized in PRESENT_EVIDENCE:
        return "present"
    if normalized in CLEAR_EVIDENCE:
        return "clear"
    return "unknown"


def _boundary_status_state(value: object) -> str:
    """Return clear / changed / unknown for boundary-change evidence."""
    normalized = _norm(value)
    if normalized in CLEAR_BOUNDARY_STATUS:
        return "clear"
    if normalized in UNRESOLVED_BOUNDARY:
        return "changed"
    return "unknown"


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
    boundary_status_state = _boundary_status_state(boundary_change_status)
    truncation_exposure = _norm(row.get("truncation_exposure"))
    survivorship_exposure = _norm(row.get("survivorship_exposure"))
    reclassification_state = _negative_evidence_state(row.get("administrative_reclassification"))
    methodology_state = _negative_evidence_state(row.get("methodology_change"))
    inconsistency_state = _negative_evidence_state(row.get("known_inconsistency"))

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
    officially_crosswalked = concordance_status == "official_crosswalk"
    boundary_resolved = boundary_fixed or harmonized or officially_crosswalked

    if not geographic_comparable:
        level_reasons.append("geography_not_comparable")
        growth_reasons.append("geography_not_comparable")

    if not temporal_comparable:
        growth_reasons.append("time_not_comparable")

    if concordance_status not in ACCEPTED_CONCORDANCE:
        growth_reasons.append("concordance_not_accepted")
        spatial_reasons.append("concordance_not_accepted")

    if not boundary_resolved:
        growth_reasons.append("boundary_not_stable_or_harmonized")

    if not harmonized:
        if boundary_status_state == "changed":
            growth_reasons.append("unresolved_boundary_change")
        elif boundary_status_state == "unknown":
            growth_reasons.append("boundary_change_status_unknown")

    if not harmonized:
        if reclassification_state == "present":
            growth_reasons.append("administrative_reclassification")
        elif reclassification_state == "unknown":
            growth_reasons.append("administrative_reclassification_unknown")

    if methodology_state == "present":
        growth_reasons.append("methodology_change")
    elif methodology_state == "unknown":
        growth_reasons.append("methodology_change_unknown")

    if inconsistency_state == "present":
        level_reasons.append("known_inconsistency")
        growth_reasons.append("known_inconsistency")
        spatial_reasons.append("known_inconsistency")
    elif inconsistency_state == "unknown":
        level_reasons.append("known_inconsistency_unknown")
        growth_reasons.append("known_inconsistency_unknown")
        spatial_reasons.append("known_inconsistency_unknown")

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
    if not harmonized:
        if boundary_status_state == "changed":
            headline_reasons.append("unresolved_boundary_change")
        elif boundary_status_state == "unknown":
            headline_reasons.append("boundary_change_status_unknown")

    if not truncation_exposure:
        headline_reasons.append("missing_truncation_exposure")
    elif truncation_exposure not in ACCEPTED_EXPOSURE:
        headline_reasons.append("truncation_exposure_unknown")
    elif truncation_exposure in BAD_EXPOSURE:
        headline_reasons.append("truncation_exposure")

    if not survivorship_exposure:
        headline_reasons.append("missing_survivorship_exposure")
    elif survivorship_exposure not in ACCEPTED_EXPOSURE:
        headline_reasons.append("survivorship_exposure_unknown")
    elif survivorship_exposure in BAD_EXPOSURE:
        headline_reasons.append("survivorship_exposure")

    if inconsistency_state == "present":
        headline_reasons.append("known_inconsistency")
    elif inconsistency_state == "unknown":
        headline_reasons.append("known_inconsistency_unknown")

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
    Existing fitness outputs are replaced so repeated evaluation is idempotent rather
    than creating duplicate columns.
    """
    out = frame.drop(columns=list(FITNESS_OUTPUT_COLUMNS), errors="ignore").copy()
    if out.empty:
        for column in FITNESS_OUTPUT_COLUMNS:
            out[column] = pd.Series(dtype="bool" if column.endswith("eligible") else "object")
        return out

    evaluated = pd.DataFrame((_evaluate_row(row) for _, row in out.iterrows()), index=out.index)
    return pd.concat([out, evaluated], axis=1)


def headline_sample(frame: pd.DataFrame) -> pd.DataFrame:
    """Evaluate fitness and return only records permitted in headline analyses."""
    evaluated = evaluate_city_data_fitness(frame)
    return evaluated.loc[evaluated["headline_eligible"]].copy()
