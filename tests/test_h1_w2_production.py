from pathlib import Path

from urban_growth.knowledge_graph.lifecycle import (
    evaluate_gate,
    hypothesis_lifecycle,
)
from urban_growth.knowledge_graph.lifecycle import (
    test_evaluation as evaluate_test_result,
)
from urban_growth.knowledge_graph.loader import load_graph
from urban_growth.knowledge_graph.models import AcceptanceGateNode, ResultNode

ROOT = Path(__file__).parents[1]


def test_w2_sequence_incomplete_then_complete_resolves_from_newer_result():
    graph = load_graph(ROOT / "knowledge" / "nodes")
    incomplete = graph.get("RESULT-H1-OOS-WUP-INCONCLUSIVE-V1")
    complete = graph.get("RESULT-H1-OOS-WUP-COMPLETE-V1")
    gate = graph.get("GATE-H1-PERSISTENCE-OOS")

    assert isinstance(incomplete, ResultNode)
    assert isinstance(complete, ResultNode)
    assert isinstance(gate, AcceptanceGateNode)

    incomplete_eval = evaluate_gate(incomplete, gate)
    assert incomplete_eval.outcome == "inconclusive"
    assert set(incomplete_eval.evaluated_metrics) == {"relative_rmse_improvement"}
    assert "mae_difference" not in incomplete.metrics

    complete_eval = evaluate_gate(complete, gate)
    assert complete_eval.outcome == "pass"
    assert complete.executed_at > incomplete.executed_at
    assert evaluate_test_result(graph, "TEST-H1-PERSISTENCE-OOS").outcome == "pass"
    assert hypothesis_lifecycle(graph, "HYP-H1") == "evidence_supported"
