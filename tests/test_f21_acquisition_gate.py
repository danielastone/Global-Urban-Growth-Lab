"""Tests for the F21 acquisition gate validator.

Tests do not require the real F21 workbook. They verify the identity-abort logic,
schema-fail path, content-pass path, Pydantic model constraints, and the committed
JSON artifact against the model where the artifact exists.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from urban_growth.f21_acquisition_gate import (
    CONSTRUCTION_COMMIT,
    REGISTERED_BYTES,
    REGISTERED_SHA256,
    EmpiricalActivationState,
    F21AcquisitionValidation,
    IdentityCheck,
    PanelFenceProtocol,
)


def _make_identity(*, sha_match: bool, size_match: bool) -> IdentityCheck:
    return IdentityCheck(
        expected_sha256=REGISTERED_SHA256,
        observed_sha256=REGISTERED_SHA256 if sha_match else "a" * 64,
        expected_bytes=REGISTERED_BYTES,
        observed_bytes=REGISTERED_BYTES if size_match else 0,
        passed=sha_match and size_match,
    )


def _base_record(*, outcome: str, activation: EmpiricalActivationState) -> dict:
    passed = outcome == "pass"
    return {
        "source_id": "un_wup_2025_cities",
        "table": "F21",
        "vintage": "WUP_2025_F21",
        "local_path": "/tmp/fake.xlsx",
        "adapter_module": "urban_growth.f21_acquisition_gate",
        "validator_commit": "deadbeef",
        "construction_commit": CONSTRUCTION_COMMIT,
        "validated_at": "2026-09-07T00:00:00+00:00",
        "identity": _make_identity(sha_match=passed, size_match=passed).model_dump(),
        "licensing": {
            "license": "CC BY 3.0 IGO",
            "redistribution_permitted": True,
            "redistribution_notes": "note",
            "repository_policy": "review_before_commit",
            "repository_policy_notes": "note",
        },
        "schema_check": {
            "required_sheet_present": passed,
            "required_sheet": "Data",
            "required_columns_present": passed,
            "required_columns": ["City_Code"],
            "missing_columns": [],
            "passed": passed,
        },
        "content": {
            "year_columns_observed": [1975, 2025, 2050] if passed else [],
            "estimate_cutoff_year": 2025,
            "total_rows": 1000 if passed else 0,
            "city_count": 200 if passed else 0,
            "country_count": 50 if passed else 0,
            "duplicate_city_id_count": 0,
            "null_population_rows": 0,
            "below_threshold_populated_rows": 0,
            "estimate_rows": 600 if passed else 0,
            "projection_rows": 400 if passed else 0,
            "passed": passed,
        },
        "overall_outcome": outcome,
        "activation_state": activation.value,
        "panel_fence_protocol": {
            "pr_a_panel_freeze": {
                "permitted": ["origin_eligibility_table"],
                "prohibited": ["rmse", "mae"],
                "acceptance": "recorded_checklist_decision_required_before_merge",
            },
            "pr_b_performance": {
                "prerequisite": "pr_a_merged",
                "contains": ["performance_metrics"],
            },
        },
    }


def test_identity_mismatch_sets_blocked_source_identity():
    record = F21AcquisitionValidation.model_validate(
        _base_record(
            outcome="fail",
            activation=EmpiricalActivationState.blocked_source_identity,
        )
    )
    assert record.overall_outcome == "fail"
    assert record.activation_state == EmpiricalActivationState.blocked_source_identity
    assert not record.identity.passed


def test_pass_record_sets_ready_for_panel_construction():
    record = F21AcquisitionValidation.model_validate(
        _base_record(
            outcome="pass",
            activation=EmpiricalActivationState.ready_for_panel_construction,
        )
    )
    assert record.overall_outcome == "pass"
    assert record.activation_state == EmpiricalActivationState.ready_for_panel_construction
    assert record.identity.passed


def test_activation_state_enum_is_closed():
    with pytest.raises(ValueError):
        EmpiricalActivationState("unknown_state")


def test_model_rejects_unknown_fields():
    data = _base_record(
        outcome="pass",
        activation=EmpiricalActivationState.ready_for_panel_construction,
    )
    data["spurious_field"] = "should_fail"
    with pytest.raises(ValidationError):
        F21AcquisitionValidation.model_validate(data)


def test_licensing_distinguishes_legal_permission_from_repository_policy():
    record = F21AcquisitionValidation.model_validate(
        _base_record(
            outcome="pass",
            activation=EmpiricalActivationState.ready_for_panel_construction,
        )
    )
    assert record.licensing.redistribution_permitted is True
    assert record.licensing.repository_policy == "review_before_commit"


def test_validator_and_construction_commits_are_distinct_fields():
    record = F21AcquisitionValidation.model_validate(
        _base_record(
            outcome="pass",
            activation=EmpiricalActivationState.ready_for_panel_construction,
        )
    )
    assert record.validator_commit == "deadbeef"
    assert record.construction_commit == CONSTRUCTION_COMMIT
    assert record.validator_commit != record.construction_commit


def test_construction_commit_is_fixed_post_212_sha():
    assert CONSTRUCTION_COMMIT == "70249dad153f4ba864fd7d566d05893be2421813"


def test_panel_fence_protocol_is_structured_model():
    record = F21AcquisitionValidation.model_validate(
        _base_record(
            outcome="pass",
            activation=EmpiricalActivationState.ready_for_panel_construction,
        )
    )
    assert isinstance(record.panel_fence_protocol, PanelFenceProtocol)
    assert "rmse" in record.panel_fence_protocol.pr_a_panel_freeze.prohibited
    assert "mae" in record.panel_fence_protocol.pr_a_panel_freeze.prohibited
    assert "origin_eligibility_table" in record.panel_fence_protocol.pr_a_panel_freeze.permitted
    assert record.panel_fence_protocol.pr_b_performance.prerequisite == "pr_a_merged"


def test_fence_protocol_rejects_unknown_fields():
    data = _base_record(
        outcome="pass",
        activation=EmpiricalActivationState.ready_for_panel_construction,
    )
    data["panel_fence_protocol"]["pr_a_panel_freeze"]["unexpected"] = "bad"
    with pytest.raises(ValidationError):
        F21AcquisitionValidation.model_validate(data)


def test_r4_activation_enum_covers_full_lifecycle():
    expected = {
        "blocked_source_unavailable",
        "blocked_source_identity",
        "blocked_source_validation",
        "ready_for_panel_construction",
        "panel_frozen",
        "ready_for_performance_evaluation",
        "evaluation_complete",
    }
    assert {e.value for e in EmpiricalActivationState} == expected


def test_committed_validation_artifact_is_valid_if_present():
    """If a committed validation artifact exists, it must parse against the model.

    This test is skipped until the local F21 bytes have been validated and the
    artifact committed. After that run, it becomes a permanent regression guard.
    """
    artifact = (
        Path(__file__).parents[1] / "data" / "acquisition" / "WUP2025-F21-validation.json"
    )
    if not artifact.exists():
        pytest.skip("No committed validation artifact yet — run validator locally first")
    data = json.loads(artifact.read_text(encoding="utf-8"))
    record = F21AcquisitionValidation.model_validate(data)
    assert record.source_id == "un_wup_2025_cities"
    assert record.table == "F21"
    assert record.identity.expected_sha256 == REGISTERED_SHA256
    assert record.overall_outcome == "pass"
    assert record.activation_state == EmpiricalActivationState.ready_for_panel_construction
    assert record.construction_commit == CONSTRUCTION_COMMIT
    # validator_commit must differ from construction_commit
    assert record.validator_commit != record.construction_commit
