from pathlib import Path

from urban_growth.knowledge_graph.lifecycle import evaluate_gate, hypothesis_lifecycle
from urban_growth.knowledge_graph.loader import load_graph
from urban_growth.knowledge_graph.models import AcceptanceGateNode, ResultNode


ROOT = Path(__file__).parents[1]


def test_w2_incomplete_result_is_inconclusive_and_h1_stays_implemented():
    graph = load_graph(ROOT / "knowledge" / "nodes")
    result = graph.get("RESULT-H1-OOS-WUP-INCONCLUSIVE-V1")
    gate = graph.get("GATE-H1-PERSISTENCE-OOS")

    assert isinstance(result, ResultNode)
    assert isinstance(gate, AcceptanceGateNode)
    evaluation = evaluate_gate(result, gate)
    assert evaluation.outcome == "inconclusive"
    assert set(evaluation.evaluated_metrics) == {"relative_rmse_improvement"}
    assert "mae_difference" not in result.metrics
    assert hypothesis_lifecycle(graph, "HYP-H1") == "implemented"
