from pathlib import Path

import pytest
from pydantic import ValidationError

from urban_growth.knowledge_graph.graph import KnowledgeGraph
from urban_growth.knowledge_graph.lifecycle import evaluate_gate, hypothesis_lifecycle
from urban_growth.knowledge_graph.loader import load_graph
from urban_growth.knowledge_graph.models import AcceptanceGateNode, ResultNode, parse_node


def test_h1_status_is_derived_without_manual_status():
    graph = load_graph(Path("knowledge/nodes"))
    assert "status" not in graph.get("HYP-H1").model_fields_set
    assert hypothesis_lifecycle(graph, "HYP-H1") == "evidence_supported"


def test_result_rejects_stored_gate_evaluation():
    payload = {
        "id": "RESULT-X",
        "type": "result",
        "title": "x",
        "canonical_name": "x",
        "test": "TEST-X",
        "status": "completed",
        "executed_at": "2026-09-06T20:00:00-04:00",
        "metrics": {"relative_rmse_improvement": 0.06, "mae_difference": -0.01},
        "execution": {"commit": "abc"},
        "gate_evaluation": {"passed": True},
    }
    with pytest.raises(ValidationError):
        parse_node(payload)


def test_gate_evaluation_is_derived_from_metrics():
    gate = AcceptanceGateNode.model_validate(
        {
            "id": "GATE-X",
            "type": "acceptance_gate",
            "title": "x",
            "canonical_name": "x gate",
            "conditions": [
                {"metric": "relative_rmse_improvement", "operator": ">=", "threshold": 0.05},
                {"metric": "mae_difference", "operator": "<=", "threshold": 0.0},
            ],
            "failure_interpretation": "falsifies_primary_claim",
        }
    )
    result = ResultNode.model_validate(
        {
            "id": "RESULT-X",
            "type": "result",
            "title": "x",
            "canonical_name": "x result",
            "test": "TEST-X",
            "status": "completed",
            "executed_at": "2026-09-06T20:00:00-04:00",
            "metrics": {"relative_rmse_improvement": 0.06, "mae_difference": -0.01},
            "execution": {"commit": "abc"},
        }
    )
    assert evaluate_gate(result, gate).outcome == "pass"


def test_missing_gate_metric_is_inconclusive():
    gate = AcceptanceGateNode.model_validate(
        {
            "id": "GATE-X",
            "type": "acceptance_gate",
            "title": "x",
            "canonical_name": "x gate",
            "conditions": [{"metric": "rmse", "operator": ">=", "threshold": 1.0}],
            "failure_interpretation": "falsifies_primary_claim",
        }
    )
    result = ResultNode.model_validate(
        {
            "id": "RESULT-X",
            "type": "result",
            "title": "x",
            "canonical_name": "x result",
            "test": "TEST-X",
            "status": "completed",
            "executed_at": "2026-09-06T20:00:00-04:00",
            "metrics": {},
            "execution": {"commit": "abc"},
        }
    )
    assert evaluate_gate(result, gate).outcome == "inconclusive"


def _r4_graph(tmp_path: Path, *, claim_scope: str, interpretation: str, metrics: dict[str, float]):
    artifact = tmp_path / "artifact.py"
    artifact.write_text("# fixture\n", encoding="utf-8")
    schema = tmp_path / "knowledge" / "schema"
    schema.mkdir(parents=True)
    schema.joinpath("lifecycle-rules.yaml").write_text(
        Path("knowledge/schema/lifecycle-rules.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    nodes = [
        parse_node(
            {
                "id": "HYP-PARENT",
                "type": "hypothesis",
                "title": "parent",
                "canonical_name": "parent",
                "claim_scope": "primary",
                "relations": [
                    {"type": "has_supporting_claim", "target": "HYP-CLAIM"},
                ],
            }
        ),
        parse_node(
            {
                "id": "HYP-CLAIM",
                "type": "hypothesis",
                "title": "claim",
                "canonical_name": "claim",
                "claim_scope": claim_scope,
                "relations": [{"type": "tested_by", "target": "TEST-X"}],
            }
        ),
        parse_node(
            {
                "id": "TEST-X",
                "type": "validation_test",
                "title": "test",
                "canonical_name": "test",
                "role": "supporting" if claim_scope == "supporting" else "primary_falsification",
                "relations": [
                    {"type": "judged_by", "target": "GATE-X"},
                    {"type": "produces", "target": "RESULT-X"},
                    {"type": "implemented_by", "target": "ART-X"},
                ],
            }
        ),
        parse_node(
            {
                "id": "GATE-X",
                "type": "acceptance_gate",
                "title": "gate",
                "canonical_name": "gate",
                "conditions": [{"metric": "score", "operator": ">=", "threshold": 1.0}],
                "failure_interpretation": interpretation,
            }
        ),
        parse_node(
            {
                "id": "RESULT-X",
                "type": "result",
                "title": "result",
                "canonical_name": "result",
                "test": "TEST-X",
                "status": "completed",
                "executed_at": "2026-09-06T20:00:00-04:00",
                "metrics": metrics,
                "execution": {"commit": "abc"},
            }
        ),
        parse_node(
            {
                "id": "ART-X",
                "type": "artifact",
                "title": "artifact",
                "canonical_name": "artifact",
                "path": "artifact.py",
            }
        ),
    ]
    return KnowledgeGraph(nodes={node.id: node for node in nodes}, repo_root=tmp_path)


def test_r4_failed_required_primary_test_is_blocking(tmp_path):
    from urban_growth.knowledge_graph.lifecycle import transition_test_disposition

    graph = _r4_graph(
        tmp_path,
        claim_scope="primary",
        interpretation="falsifies_primary_claim",
        metrics={"score": 0.0},
    )
    assert (
        transition_test_disposition(graph, "HYP-CLAIM", "TEST-X", "evidence_supported")
        == "blocking_failure"
    )


def test_r4_missing_metric_is_inconclusive_not_blocking(tmp_path):
    from urban_growth.knowledge_graph.lifecycle import transition_test_disposition

    graph = _r4_graph(
        tmp_path,
        claim_scope="primary",
        interpretation="falsifies_primary_claim",
        metrics={},
    )
    assert (
        transition_test_disposition(graph, "HYP-CLAIM", "TEST-X", "evidence_supported")
        == "inconclusive"
    )


def test_r4_supporting_claim_failure_is_diagnostic_for_parent(tmp_path):
    from urban_growth.knowledge_graph.lifecycle import transition_test_disposition

    graph = _r4_graph(
        tmp_path,
        claim_scope="supporting",
        interpretation="contradicts_supporting_claim",
        metrics={"score": 0.0},
    )
    assert (
        transition_test_disposition(graph, "HYP-PARENT", "TEST-X", "evidence_supported")
        == "diagnostic"
    )
    assert (
        transition_test_disposition(graph, "HYP-CLAIM", "TEST-X", "evidence_supported")
        == "blocking_failure"
    )


def test_r4_passing_required_test_is_pass(tmp_path):
    from urban_growth.knowledge_graph.lifecycle import transition_test_disposition

    graph = _r4_graph(
        tmp_path,
        claim_scope="primary",
        interpretation="falsifies_primary_claim",
        metrics={"score": 1.1},
    )
    assert transition_test_disposition(graph, "HYP-CLAIM", "TEST-X", "evidence_supported") == "pass"


def test_lifecycle_rules_file_drives_data_readiness(tmp_path):
    source = Path("knowledge")
    target = tmp_path / "knowledge"
    target.mkdir()
    (target / "nodes").symlink_to(source.resolve() / "nodes", target_is_directory=True)
    (target / "schema").mkdir()
    original = (source / "schema" / "lifecycle-rules.yaml").read_text(encoding="utf-8")
    altered = original.replace(
        "requires_dataset_availability: [ingested, validated]",
        "requires_dataset_availability: [validated]",
    )
    assert altered != original
    (target / "schema" / "lifecycle-rules.yaml").write_text(altered, encoding="utf-8")
    (target / "schema" / "relation-types.yaml").write_text(
        (source / "schema" / "relation-types.yaml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    graph = load_graph(target / "nodes")
    assert hypothesis_lifecycle(graph, "HYP-H1") == "specified"
