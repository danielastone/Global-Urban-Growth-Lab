"""Deterministic missingness states for population-reliability evidence.

An assessment is scoped to a country, dimension, use case, reference date, and
source release.  The state describes evidence availability, not country quality.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date
from typing import Any

ASSESSMENT_STATES = {"scored", "partially_observed", "unassessable"}
REASON_CODES = {
    "source_not_covered",
    "source_value_missing",
    "source_value_stale_for_use",
    "invalid_source_value",
    "country_crosswalk_unresolved",
    "conflicting_evidence_unresolved",
    "required_field_partial",
    "required_field_complete",
}


class ReliabilityAssessmentError(ValueError):
    """Raised when assessment primitives violate the missingness contract."""


def _text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ReliabilityAssessmentError(f"{field} must be normalized non-empty text")
    return value


def _date(value: str, *, field: str) -> str:
    _text(value, field=field)
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise ReliabilityAssessmentError(f"{field} must be an ISO date") from error
    return value


def _field_set(values: Iterable[str], *, field: str, allow_empty: bool = True) -> tuple[str, ...]:
    rows = tuple(values)
    for value in rows:
        _text(value, field=field)
    if not allow_empty and not rows:
        raise ReliabilityAssessmentError(f"{field} must not be empty")
    if len(rows) != len(set(rows)):
        raise ReliabilityAssessmentError(f"{field} must contain unique fields")
    return tuple(sorted(rows))


def _is_observed(value: Any) -> bool:
    return value is not None and not (isinstance(value, str) and not value.strip())


@dataclass(frozen=True)
class ReliabilityAssessment:
    country_id: str
    dimension_id: str
    use_case_id: str
    reference_date: str
    source_release: str
    expected_fields: tuple[str, ...]
    observed_fields: tuple[str, ...]
    assessment_state: str
    reason_codes: tuple[str, ...]
    transformation_run_id: str

    def as_dict(self) -> dict[str, Any]:
        """Return a serialization-ready record without converting tuples to text."""
        return {
            "country_id": self.country_id,
            "dimension_id": self.dimension_id,
            "use_case_id": self.use_case_id,
            "reference_date": self.reference_date,
            "source_release": self.source_release,
            "expected_fields": list(self.expected_fields),
            "observed_fields": list(self.observed_fields),
            "assessment_state": self.assessment_state,
            "reason_codes": list(self.reason_codes),
            "transformation_run_id": self.transformation_run_id,
        }


def derive_assessment(
    *,
    country_id: str,
    dimension_id: str,
    use_case_id: str,
    reference_date: str,
    source_release: str,
    expected_fields: Iterable[str],
    field_values: Mapping[str, Any],
    transformation_run_id: str,
    source_covered: bool = True,
    country_crosswalk_resolved: bool = True,
    stale_fields: Iterable[str] = (),
    invalid_fields: Iterable[str] = (),
    conflicting_fields: Iterable[str] = (),
) -> ReliabilityAssessment:
    """Derive one assessment from explicit evidence primitives.

    Missing, stale, invalid, conflicting, and unmatched evidence are never assigned
    an adverse numeric value.  They remain separate machine-readable reasons.
    """
    identity = {
        "country_id": _text(country_id, field="country_id"),
        "dimension_id": _text(dimension_id, field="dimension_id"),
        "use_case_id": _text(use_case_id, field="use_case_id"),
        "reference_date": _date(reference_date, field="reference_date"),
        "source_release": _text(source_release, field="source_release"),
        "transformation_run_id": _text(
            transformation_run_id, field="transformation_run_id"
        ),
    }
    expected = _field_set(expected_fields, field="expected_fields", allow_empty=False)
    unexpected_values = sorted(set(field_values).difference(expected))
    if unexpected_values:
        raise ReliabilityAssessmentError(
            f"field_values contains fields outside expected_fields: {unexpected_values}"
        )

    problem_sets = {
        "stale_fields": set(_field_set(stale_fields, field="stale_fields")),
        "invalid_fields": set(_field_set(invalid_fields, field="invalid_fields")),
        "conflicting_fields": set(
            _field_set(conflicting_fields, field="conflicting_fields")
        ),
    }
    for label, fields in problem_sets.items():
        unknown = sorted(fields.difference(expected))
        if unknown:
            raise ReliabilityAssessmentError(f"{label} contains unexpected fields: {unknown}")
    labels = list(problem_sets)
    for index, left in enumerate(labels):
        for right in labels[index + 1 :]:
            overlap = sorted(problem_sets[left].intersection(problem_sets[right]))
            if overlap:
                raise ReliabilityAssessmentError(
                    f"Evidence fields cannot have conflicting failure states: {overlap}"
                )

    supplied = {field for field, value in field_values.items() if _is_observed(value)}
    if not source_covered and supplied:
        raise ReliabilityAssessmentError("source_covered=False conflicts with supplied evidence")

    reasons: set[str] = set()
    if not country_crosswalk_resolved:
        observed: set[str] = set()
        reasons.add("country_crosswalk_unresolved")
    elif not source_covered:
        observed = set()
        reasons.add("source_not_covered")
    else:
        excluded = set().union(*problem_sets.values())
        observed = supplied.difference(excluded)
        missing = set(expected).difference(supplied)
        if missing:
            reasons.add("source_value_missing")
        if problem_sets["stale_fields"]:
            reasons.add("source_value_stale_for_use")
        if problem_sets["invalid_fields"]:
            reasons.add("invalid_source_value")
        if problem_sets["conflicting_fields"]:
            reasons.add("conflicting_evidence_unresolved")

    if len(observed) == len(expected):
        state = "scored"
        reasons = {"required_field_complete"}
    elif observed:
        state = "partially_observed"
        reasons.add("required_field_partial")
    else:
        state = "unassessable"
        if not reasons:
            reasons.add("source_value_missing")

    record = ReliabilityAssessment(
        **identity,
        expected_fields=expected,
        observed_fields=tuple(sorted(observed)),
        assessment_state=state,
        reason_codes=tuple(sorted(reasons)),
    )
    validate_assessment(record)
    return record


def validate_assessment(record: ReliabilityAssessment) -> None:
    """Validate canonical state, field sets, and reason/state compatibility."""
    _text(record.country_id, field="country_id")
    _text(record.dimension_id, field="dimension_id")
    _text(record.use_case_id, field="use_case_id")
    _date(record.reference_date, field="reference_date")
    _text(record.source_release, field="source_release")
    _text(record.transformation_run_id, field="transformation_run_id")
    expected = _field_set(record.expected_fields, field="expected_fields", allow_empty=False)
    observed = _field_set(record.observed_fields, field="observed_fields")
    reasons = _field_set(record.reason_codes, field="reason_codes", allow_empty=False)
    if expected != record.expected_fields or observed != record.observed_fields:
        raise ReliabilityAssessmentError("field sets must be canonically sorted")
    if reasons != record.reason_codes:
        raise ReliabilityAssessmentError("reason_codes must be canonically sorted")
    unknown_reasons = sorted(set(reasons).difference(REASON_CODES))
    if unknown_reasons:
        raise ReliabilityAssessmentError(f"Unknown reason_codes: {unknown_reasons}")
    if not set(observed).issubset(expected):
        raise ReliabilityAssessmentError("observed_fields must be a subset of expected_fields")
    if record.assessment_state not in ASSESSMENT_STATES:
        raise ReliabilityAssessmentError("assessment_state is not allowed")

    complete = len(observed) == len(expected)
    if record.assessment_state == "scored":
        if not complete or reasons != ("required_field_complete",):
            raise ReliabilityAssessmentError("scored requires complete fields and complete reason")
    elif record.assessment_state == "partially_observed":
        if not observed or complete or "required_field_partial" not in reasons:
            raise ReliabilityAssessmentError("partially_observed requires an incomplete usable subset")
    elif observed:
        raise ReliabilityAssessmentError("unassessable cannot contain observed_fields")


def assessment_state_counts(
    records: Iterable[ReliabilityAssessment],
) -> dict[str, int]:
    """Count country-assessment rows by state without dropping zero-count states."""
    counts = {state: 0 for state in sorted(ASSESSMENT_STATES)}
    identities: set[tuple[str, str, str, str, str]] = set()
    for record in records:
        validate_assessment(record)
        identity = (
            record.country_id,
            record.dimension_id,
            record.use_case_id,
            record.reference_date,
            record.source_release,
        )
        if identity in identities:
            raise ReliabilityAssessmentError("Duplicate assessment scope")
        identities.add(identity)
        counts[record.assessment_state] += 1
    return counts
