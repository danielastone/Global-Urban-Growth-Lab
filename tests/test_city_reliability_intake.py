from copy import deepcopy

import pytest

from urban_growth.city_reliability_intake import CityReliabilityIntakeError, validate_intake


def _payload() -> dict:
    unknown = {"value": "unknown", "notes": "No reviewed evidence yet."}
    return {
        "verification": {
            "value": "place_direct",
            "source_id": "source",
            "snapshot_id": "snapshot",
            "source_release": "2025 release",
            "observation_date": "2025-01-01",
            "citation": "Table 2, row 3",
        },
        "incentive": deepcopy(unknown),
        "aggregate_check": deepcopy(unknown),
        "conduit": deepcopy(unknown),
        "granular_treatment": deepcopy(unknown),
    }


def _validate(payload: dict) -> dict:
    return validate_intake(
        payload,
        location_id="USA-PLACE-123",
        location_label="Example place",
        reference_date="2026-09-03",
        use_case_id="descriptive_city_evidence_v1",
        submitted_by="analyst",
    )


def test_intake_preserves_signals_and_prohibits_analytical_use() -> None:
    record = _validate(_payload())
    assert record["analytical_use_authorized"] is False
    assert record["record_status"] == "staged_documentary_evidence"
    assert record["signals"]["verification"]["value"] == "place_direct"
    assert not {"score", "band", "tier", "archetype"}.intersection(record)


def test_missing_evidence_is_explicit_unknown_without_fake_provenance() -> None:
    payload = _payload()
    payload["incentive"]["snapshot_id"] = "placeholder"
    with pytest.raises(CityReliabilityIntakeError, match="unknown but supplies"):
        _validate(payload)


def test_observed_assertion_requires_dated_provenance() -> None:
    payload = _payload()
    del payload["verification"]["snapshot_id"]
    with pytest.raises(CityReliabilityIntakeError, match="snapshot_id"):
        _validate(payload)
    payload = _payload()
    payload["verification"]["observation_date"] = "2025"
    with pytest.raises(CityReliabilityIntakeError, match="ISO date"):
        _validate(payload)


@pytest.mark.parametrize("forbidden", ["score", "band", "tier", "archetype", "classification"])
def test_composite_outputs_are_rejected(forbidden: str) -> None:
    payload = _payload()
    payload[forbidden] = "high"
    with pytest.raises(CityReliabilityIntakeError, match="Composite outputs are prohibited"):
        _validate(payload)


def test_signal_set_and_controlled_values_fail_closed() -> None:
    payload = _payload()
    del payload["conduit"]
    with pytest.raises(CityReliabilityIntakeError, match="Signal set mismatch"):
        _validate(payload)
    payload = _payload()
    payload["verification"]["value"] = "2"
    with pytest.raises(CityReliabilityIntakeError, match="must be one of"):
        _validate(payload)
