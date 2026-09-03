from dataclasses import replace

import pytest

from urban_growth.reliability_assessment import (
    ReliabilityAssessmentError,
    assessment_state_counts,
    derive_assessment,
    validate_assessment,
)

BASE = {
    "country_id": "USA",
    "dimension_id": "spi_data_sources",
    "use_case_id": "descriptive_matrix_v1",
    "reference_date": "2025-12-31",
    "source_release": "SPI 2025",
    "expected_fields": ["civil_registration", "population_census"],
    "transformation_run_id": "transform:example",
}


def test_complete_fields_are_scored_without_a_quality_inference() -> None:
    record = derive_assessment(
        **BASE,
        field_values={"civil_registration": 0.0, "population_census": False},
    )
    assert record.assessment_state == "scored"
    assert record.observed_fields == ("civil_registration", "population_census")
    assert record.reason_codes == ("required_field_complete",)
    assert record.as_dict()["assessment_state"] == "scored"


def test_partial_fields_preserve_missingness_instead_of_imputing_adverse_values() -> None:
    record = derive_assessment(
        **BASE,
        field_values={"population_census": 72.0, "civil_registration": None},
    )
    assert record.assessment_state == "partially_observed"
    assert record.observed_fields == ("population_census",)
    assert record.reason_codes == ("required_field_partial", "source_value_missing")


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"field_values": {}, "source_covered": False}, "source_not_covered"),
        ({"field_values": {}}, "source_value_missing"),
        (
            {"field_values": {"population_census": 1}, "country_crosswalk_resolved": False},
            "country_crosswalk_unresolved",
        ),
    ],
)
def test_unassessable_causes_remain_distinct(kwargs: dict, reason: str) -> None:
    record = derive_assessment(**BASE, **kwargs)
    assert record.assessment_state == "unassessable"
    assert record.observed_fields == ()
    assert record.reason_codes == (reason,)


def test_invalid_stale_and_conflicting_fields_are_not_counted_as_observed() -> None:
    record = derive_assessment(
        **BASE,
        field_values={"civil_registration": 20, "population_census": 80},
        stale_fields=["civil_registration"],
    )
    assert record.assessment_state == "partially_observed"
    assert record.observed_fields == ("population_census",)
    assert record.reason_codes == (
        "required_field_partial",
        "source_value_stale_for_use",
    )

    invalid = derive_assessment(
        **BASE,
        field_values={"civil_registration": -1},
        invalid_fields=["civil_registration"],
    )
    assert invalid.assessment_state == "unassessable"
    assert invalid.reason_codes == ("invalid_source_value", "source_value_missing")

    conflict = derive_assessment(
        **BASE,
        field_values={"civil_registration": 20},
        conflicting_fields=["civil_registration"],
    )
    assert conflict.assessment_state == "unassessable"
    assert conflict.reason_codes == (
        "conflicting_evidence_unresolved",
        "source_value_missing",
    )


def test_state_is_scoped_by_use_case_and_reference_date() -> None:
    current = derive_assessment(
        **BASE,
        field_values={"civil_registration": 20, "population_census": 80},
    )
    forecast = derive_assessment(
        **{**BASE, "use_case_id": "forecast_origin_2020", "reference_date": "2020-12-31"},
        field_values={"civil_registration": 20, "population_census": 80},
        stale_fields=["civil_registration", "population_census"],
    )
    assert current.assessment_state == "scored"
    assert forecast.assessment_state == "unassessable"
    assert forecast.reason_codes == ("source_value_stale_for_use",)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"expected_fields": []}, "must not be empty"),
        ({"field_values": {"invented": 1}}, "outside expected_fields"),
        (
            {
                "field_values": {"population_census": 1},
                "source_covered": False,
            },
            "conflicts with supplied evidence",
        ),
        (
            {
                "field_values": {"population_census": 1},
                "stale_fields": ["population_census"],
                "invalid_fields": ["population_census"],
            },
            "conflicting failure states",
        ),
    ],
)
def test_contradictory_or_unknown_primitives_fail_closed(kwargs: dict, message: str) -> None:
    inputs = {**BASE, **kwargs}
    inputs.setdefault("field_values", {})
    with pytest.raises(ReliabilityAssessmentError, match=message):
        derive_assessment(**inputs)


def test_record_validation_rejects_invented_state_and_noncanonical_fields() -> None:
    record = derive_assessment(
        **BASE,
        field_values={"civil_registration": 1, "population_census": 2},
    )
    with pytest.raises(ReliabilityAssessmentError, match="not allowed"):
        validate_assessment(replace(record, assessment_state="high_quality"))
    with pytest.raises(ReliabilityAssessmentError, match="canonically sorted"):
        validate_assessment(
            replace(record, expected_fields=("population_census", "civil_registration"))
        )


def test_country_counts_keep_zero_states_and_reject_duplicate_scope() -> None:
    record = derive_assessment(**BASE, field_values={})
    assert assessment_state_counts([record]) == {
        "partially_observed": 0,
        "scored": 0,
        "unassessable": 1,
    }
    with pytest.raises(ReliabilityAssessmentError, match="Duplicate assessment scope"):
        assessment_state_counts([record, record])
