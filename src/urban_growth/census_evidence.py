"""Vintage-qualified census-event and estimate-incorporation evidence contracts."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date

ENUMERATION_BASES = {"de_facto", "de_jure", "register_based", "combined", "unknown"}
GEOGRAPHIC_COVERAGE = {"national", "partial", "excluded_areas", "unknown"}
RESULTS_STATUSES = {"preliminary", "final", "partially_published", "unpublished", "unknown"}
PES_STATUSES = {"none_reported", "planned", "conducted", "published", "unknown"}
YES_NO_UNKNOWN = {"yes", "no", "unknown"}
INCORPORATION = {"yes", "partially", "no", "unknown"}
EVIDENCE_LEVELS = {"explicit", "inferred_documented", "unknown"}


class CensusEvidenceError(ValueError):
    """Raised when census evidence violates its documentary contract."""


def _text(value: str, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise CensusEvidenceError(f"{field} must be normalized non-empty text")
    return value


def _date(value: str | None, field: str, *, required: bool = False) -> date | None:
    if value is None:
        if required:
            raise CensusEvidenceError(f"{field} is required")
        return None
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise CensusEvidenceError(f"{field} must be an ISO date") from error


def census_event_id_for(country_id: str, reference_date: str, source_id: str) -> str:
    payload = "|".join(
        (_text(country_id, "country_id"), reference_date, _text(source_id, "source_id"))
    )
    _date(reference_date, "census_reference_date", required=True)
    return "census:" + hashlib.sha256(payload.encode()).hexdigest()


@dataclass(frozen=True)
class CensusEvent:
    census_event_id: str
    country_id: str
    census_round: str
    census_reference_date: str
    enumeration_start_date: str | None
    enumeration_basis: str
    geographic_coverage: str
    geographic_coverage_source_text: str
    results_status: str
    post_enumeration_survey_status: str
    pes_results_published: str
    estimated_net_undercount: float | None
    official_coverage_adjustment_applied: str
    source_id: str
    snapshot_id: str


@dataclass(frozen=True)
class EstimateIncorporation:
    country_id: str
    estimate_series: str
    estimate_vintage: str
    census_event_id: str
    census_incorporated: str
    incorporation_method: str
    source_evidence_level: str
    source_id: str
    snapshot_id: str


def validate_census_events(events: Iterable[CensusEvent]) -> None:
    rows = list(events)
    identities: set[tuple[str, str]] = set()
    for row in rows:
        for field in ("country_id", "census_round", "source_id", "snapshot_id"):
            _text(getattr(row, field), field)
        reference = _date(row.census_reference_date, "census_reference_date", required=True)
        start = _date(row.enumeration_start_date, "enumeration_start_date")
        if start and reference and start > reference:
            raise CensusEvidenceError("enumeration_start_date cannot follow census_reference_date")
        expected_id = census_event_id_for(row.country_id, row.census_reference_date, row.source_id)
        if row.census_event_id != expected_id:
            raise CensusEvidenceError("census_event_id does not match country, date, and source")
        vocabularies = {
            "enumeration_basis": ENUMERATION_BASES,
            "geographic_coverage": GEOGRAPHIC_COVERAGE,
            "results_status": RESULTS_STATUSES,
            "post_enumeration_survey_status": PES_STATUSES,
            "pes_results_published": YES_NO_UNKNOWN,
            "official_coverage_adjustment_applied": YES_NO_UNKNOWN,
        }
        for field, allowed in vocabularies.items():
            if getattr(row, field) not in allowed:
                raise CensusEvidenceError(f"{field} has an invalid value")
        _text(row.geographic_coverage_source_text, "geographic_coverage_source_text")
        if (
            row.estimated_net_undercount is not None
            and not -100 <= row.estimated_net_undercount <= 100
        ):
            raise CensusEvidenceError(
                "estimated_net_undercount must be a source percentage in [-100, 100]"
            )
        if row.post_enumeration_survey_status == "published" and row.pes_results_published != "yes":
            raise CensusEvidenceError("published PES status requires pes_results_published=yes")
        identity = (row.census_event_id, row.snapshot_id)
        if identity in identities:
            raise CensusEvidenceError("duplicate census assertion")
        identities.add(identity)


def validate_estimate_incorporations(
    records: Iterable[EstimateIncorporation], *, events: Iterable[CensusEvent]
) -> None:
    event_ids = {row.census_event_id for row in events}
    identities: set[tuple[str, str, str, str, str]] = set()
    for row in records:
        for field in (
            "country_id",
            "estimate_series",
            "estimate_vintage",
            "census_event_id",
            "source_id",
            "snapshot_id",
        ):
            _text(getattr(row, field), field)
        if row.census_event_id not in event_ids:
            raise CensusEvidenceError("estimate incorporation references an unknown census event")
        if row.census_incorporated not in INCORPORATION:
            raise CensusEvidenceError("census_incorporated has an invalid value")
        if row.source_evidence_level not in EVIDENCE_LEVELS:
            raise CensusEvidenceError("source_evidence_level has an invalid value")
        if row.source_evidence_level == "unknown":
            if row.census_incorporated != "unknown" or row.incorporation_method != "unknown":
                raise CensusEvidenceError("unknown evidence cannot assert incorporation or method")
        else:
            _text(row.incorporation_method, "incorporation_method")
        identity = (
            row.country_id,
            row.estimate_series,
            row.estimate_vintage,
            row.census_event_id,
            row.snapshot_id,
        )
        if identity in identities:
            raise CensusEvidenceError("duplicate estimate-incorporation assertion")
        identities.add(identity)
