"""Validate staged, city-level documentary reliability evidence.

This module deliberately does not calculate a score, band, archetype, or eligibility
decision.  It creates a reviewable intake record that must still be promoted through the
repository's snapshot and transformation registries before analytical use.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import date
from typing import Any

SIGNAL_VALUES = {
    "verification": {"none_documented", "country_level_only", "place_direct", "unknown"},
    "incentive": {
        "aligned_distortion_risk",
        "heterogeneous_incentives",
        "no_documented_incentive",
        "unknown",
    },
    "aggregate_check": {"none_documented", "partial", "strong", "unknown"},
    "conduit": {"obscured", "ordinary", "heightened_scrutiny", "unknown"},
    "granular_treatment": {
        "suspected_undisclosed",
        "disclosed_bounded",
        "no_issue_documented",
        "unknown",
    },
}

ASSERTION_FIELDS = {
    "value",
    "source_id",
    "snapshot_id",
    "source_release",
    "observation_date",
    "citation",
    "notes",
}


class CityReliabilityIntakeError(ValueError):
    """Raised when a staged documentary record violates the intake contract."""


def _date(value: Any, *, field: str) -> str:
    if not isinstance(value, str):
        raise CityReliabilityIntakeError(f"{field} must be an ISO date")
    try:
        date.fromisoformat(value)
    except ValueError as error:
        raise CityReliabilityIntakeError(f"{field} must be an ISO date") from error
    return value


def _text(value: Any, *, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CityReliabilityIntakeError(f"{field} must be non-empty text")
    return value.strip()


def validate_intake(
    payload: Mapping[str, Any],
    *,
    location_id: str,
    location_label: str,
    reference_date: str,
    use_case_id: str,
    submitted_by: str,
) -> dict[str, Any]:
    """Return a canonical staged record without combining documentary signals."""
    forbidden = {"score", "band", "tier", "archetype", "classification"}
    present_forbidden = sorted(forbidden.intersection(payload))
    if present_forbidden:
        raise CityReliabilityIntakeError(
            "Composite outputs are prohibited: " + ", ".join(present_forbidden)
        )

    unknown_signals = sorted(set(payload).difference(SIGNAL_VALUES))
    missing_signals = sorted(set(SIGNAL_VALUES).difference(payload))
    if unknown_signals or missing_signals:
        raise CityReliabilityIntakeError(
            f"Signal set mismatch; missing={missing_signals}, unknown={unknown_signals}"
        )

    assertions: dict[str, dict[str, str]] = {}
    for signal, allowed_values in SIGNAL_VALUES.items():
        raw = payload[signal]
        if not isinstance(raw, Mapping):
            raise CityReliabilityIntakeError(f"{signal} must be an object")
        extra = sorted(set(raw).difference(ASSERTION_FIELDS))
        if extra:
            raise CityReliabilityIntakeError(f"{signal} has unknown fields: {extra}")
        value = _text(raw.get("value"), field=f"{signal}.value")
        if value not in allowed_values:
            raise CityReliabilityIntakeError(
                f"{signal}.value must be one of {sorted(allowed_values)}"
            )

        assertion = {"value": value}
        if value == "unknown":
            assertion["notes"] = _text(raw.get("notes"), field=f"{signal}.notes")
            # Unknown is a real missingness state; invented placeholder provenance is worse.
            supplied_provenance = sorted(
                key for key in ASSERTION_FIELDS - {"value", "notes"} if raw.get(key)
            )
            if supplied_provenance:
                raise CityReliabilityIntakeError(
                    f"{signal} is unknown but supplies assertion provenance: {supplied_provenance}"
                )
        else:
            for field in ("source_id", "snapshot_id", "source_release", "citation"):
                assertion[field] = _text(raw.get(field), field=f"{signal}.{field}")
            assertion["observation_date"] = _date(
                raw.get("observation_date"), field=f"{signal}.observation_date"
            )
            if raw.get("notes"):
                assertion["notes"] = _text(raw["notes"], field=f"{signal}.notes")
        assertions[signal] = assertion

    return {
        "schema_version": "city_reliability_intake_v1",
        "record_status": "staged_documentary_evidence",
        "analytical_use_authorized": False,
        "location_id": _text(location_id, field="location_id"),
        "location_label": _text(location_label, field="location_label"),
        "reference_date": _date(reference_date, field="reference_date"),
        "use_case_id": _text(use_case_id, field="use_case_id"),
        "submitted_by": _text(submitted_by, field="submitted_by"),
        "signals": assertions,
        "promotion_requirements": [
            "verify each non-unknown snapshot_id against data/reliability_snapshots.csv",
            "create a registered deterministic transformation run",
            "apply the use-specific city data fitness gate separately",
        ],
    }


def canonical_json(record: Mapping[str, Any]) -> str:
    return json.dumps(record, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
