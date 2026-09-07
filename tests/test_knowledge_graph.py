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
    evaluation = evaluate_gate(result, gate)
    assert evaluation.outcome == "pass"
    assert evaluation.evaluated_metrics == {
        "relative_rmse_improvement": 0.06,
        "mae_difference": -0.01,
    }


def test_result_incomplete_metrics_are_inconclusive():
    gate = AcceptanceGateNode.model_validate(
        {
            "id": "GATE-X",
            "type": "acceptance_gate",
            "title": "x",
            "canonical_name": "x gate incomplete",
            "conditions": [
                {"metric": "relative_rmse_improvement", "operator": ">=", "threshold": 0.05},
                {"metric": "mae_difference", "operator": "<=", "threshold": 0.0},
            ],
            "failure_interpretation": "falsifies_primary_claim",
        }
    )
    result = ResultNode.model_validate(
        {
            "id": "RESULT-X-INCOMPLETE",
            "type": "result",
            "title": "x incomplete",
            "canonical_name": "x incomplete result",
            "test": "TEST-X",
            "status": "completed",
            "executed_at": "2026-09-06T20:00:00-04:00",
            "metrics": {"relative_rmse_improvement": 0.06},
            "execution": {"commit": "abc"},
        }
    )
    evaluation = evaluate_gate(result, gate)
    assert evaluation.outcome == "inconclusive"


def test_graph_rejects_illegal_relation_topology():
    graph = KnowledgeGraph(nodes={}, repo_root=Path("."))
    assert graph.nodes == {}
