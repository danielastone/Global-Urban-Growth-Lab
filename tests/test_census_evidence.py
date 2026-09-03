from dataclasses import replace

import pytest

from urban_growth.census_evidence import (
    CensusEvent,
    CensusEvidenceError,
    EstimateIncorporation,
    census_event_id_for,
    validate_census_events,
    validate_estimate_incorporations,
)


def event(**changes):
    values = {
        "country_id": "USA",
        "census_round": "2020",
        "census_reference_date": "2020-04-01",
        "enumeration_start_date": "2020-03-01",
        "enumeration_basis": "de_jure",
        "geographic_coverage": "national",
        "geographic_coverage_source_text": "50 states and DC",
        "results_status": "final",
        "post_enumeration_survey_status": "published",
        "pes_results_published": "yes",
        "estimated_net_undercount": -0.24,
        "official_coverage_adjustment_applied": "no",
        "source_id": "unsd_census_dates",
        "snapshot_id": "snapshot:one",
    }
    values.update(changes)
    values.setdefault(
        "census_event_id",
        census_event_id_for(
            values["country_id"], values["census_reference_date"], values["source_id"]
        ),
    )
    return CensusEvent(**values)


def incorporation(census_event_id, **changes):
    values = {
        "country_id": "USA",
        "estimate_series": "WPP",
        "estimate_vintage": "2024 Revision",
        "census_event_id": census_event_id,
        "census_incorporated": "yes",
        "incorporation_method": "Publisher country note identifies 2020 census",
        "source_evidence_level": "explicit",
        "source_id": "un_wpp_2024",
        "snapshot_id": "snapshot:wpp",
    }
    values.update(changes)
    return EstimateIncorporation(**values)


def test_valid_records_preserve_event_and_vintage_qualified_incorporation():
    e = event()
    validate_census_events([e])
    validate_estimate_incorporations([incorporation(e.census_event_id)], events=[e])


def test_conflicting_sources_are_separate_assertions_not_overwritten():
    a = event()
    b = event(source_id="unfpa_census", snapshot_id="snapshot:two", results_status="preliminary")
    validate_census_events([a, b])
    assert a.census_event_id != b.census_event_id


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"enumeration_start_date": "2020-05-01"}, "cannot follow"),
        ({"enumeration_basis": "assumed"}, "invalid value"),
        ({"estimated_net_undercount": 101}, "source percentage"),
        (
            {"post_enumeration_survey_status": "published", "pes_results_published": "unknown"},
            "requires",
        ),
    ],
)
def test_event_chronology_vocabulary_and_consistency_fail_closed(changes, message):
    with pytest.raises(CensusEvidenceError, match=message):
        validate_census_events([event(**changes)])


def test_unknown_incorporation_cannot_hide_an_analyst_inference():
    e = event()
    row = incorporation(
        e.census_event_id, source_evidence_level="unknown", census_incorporated="yes"
    )
    with pytest.raises(CensusEvidenceError, match="unknown evidence"):
        validate_estimate_incorporations([row], events=[e])
    validate_estimate_incorporations(
        [replace(row, census_incorporated="unknown", incorporation_method="unknown")], events=[e]
    )


def test_incorporation_requires_registered_event_and_unique_assertion():
    e = event()
    row = incorporation(e.census_event_id)
    with pytest.raises(CensusEvidenceError, match="unknown census event"):
        validate_estimate_incorporations([row], events=[])
    with pytest.raises(CensusEvidenceError, match="duplicate"):
        validate_estimate_incorporations([row, row], events=[e])
