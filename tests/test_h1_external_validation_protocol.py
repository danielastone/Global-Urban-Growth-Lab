from pathlib import Path

from pydantic import ValidationError
import pytest

from urban_growth.knowledge_graph.graph import KnowledgeGraph
from urban_growth.knowledge_graph.lifecycle import external_validation_scope, hypothesis_lifecycle
from urban_growth.knowledge_graph.loader import load_graph
from urban_growth.knowledge_graph.models import (
    Relation,
    ResultExecution,
    ResultNode,
    ValidationType,
)
from urban_growth.knowledge_graph.validate import validate_graph


HYPOTHESIS_ID = "HYP-H1"
TEST_ID = "TEST-H1-MEXICO-DIRECT-COUNT-10Y-OOS"
GATE_ID = "GATE-H1-DIRECT-COUNT-10Y-OOS"
GEOGRAPHY_ID = "GEO-MEXICO"


def _repo_graph() -> KnowledgeGraph:
    return load_graph(Path("knowledge/nodes"))


def _graph_with_result(validation_type: ValidationType, geography: str | None) -> KnowledgeGraph:
    graph = _repo_graph()
    test = graph.get(TEST_ID)
    result = ResultNode(
        id="RESULT-H1-MEXICO-DIRECT-COUNT-10Y-OOS-SYNTHETIC",
        type="result",
        title="Synthetic external lifecycle result",
        canonical_name="Synthetic H1 Mexico external lifecycle result",
        aliases=[],
        test=TEST_ID,
        status="completed",
        executed_at="2099-01-01T00:00:00+00:00",
        validation_type=validation_type,
        geography=geography,
        metrics={"relative_rmse_improvement": 0.06, "mae_difference": -0.001},
        execution=ResultExecution(commit="0" * 40),
        sample={},
        inputs={},
        relations=[],
    )
    updated_test = test.model_copy(
        update={"relations": [*test.relations, Relation(type="produces", target=result.id)]}
    )
    nodes = dict(graph.nodes)
    nodes[TEST_ID] = updated_test
    nodes[result.id] = result
    return KnowledgeGraph(nodes=nodes, repo_root=graph.repo_root)


def test_pending_mexico_external_test_does_not_regress_h1() -> None:
    graph = _repo_graph()
    assert validate_graph(graph) == []
    assert hypothesis_lifecycle(graph, HYPOTHESIS_ID) == "evidence_supported"
    assert external_validation_scope(graph, HYPOTHESIS_ID) == ()
    assert graph.get(TEST_ID).horizon_years == 10
    assert graph.get(GATE_ID).horizon_years == 10


def test_direct_count_external_pass_advances_with_derived_scope() -> None:
    graph = _graph_with_result(ValidationType.direct_count_external, GEOGRAPHY_ID)
    assert validate_graph(graph) == []
    assert external_validation_scope(graph, HYPOTHESIS_ID) == (GEOGRAPHY_ID,)
    assert hypothesis_lifecycle(graph, HYPOTHESIS_ID) == "externally_validated"


def test_non_direct_count_pass_does_not_advance_external_lifecycle() -> None:
    graph = _graph_with_result(ValidationType.internal, GEOGRAPHY_ID)
    assert validate_graph(graph) == []
    assert external_validation_scope(graph, HYPOTHESIS_ID) == ()
    assert hypothesis_lifecycle(graph, HYPOTHESIS_ID) == "evidence_supported"


def test_direct_count_external_result_requires_geography() -> None:
    with pytest.raises(ValidationError, match="direct_count_external results require geography"):
        ResultNode(
            id="RESULT-BAD",
            type="result",
            title="Bad result",
            canonical_name="Bad result",
            aliases=[],
            test=TEST_ID,
            status="completed",
            executed_at="2099-01-01T00:00:00+00:00",
            validation_type=ValidationType.direct_count_external,
            geography=None,
            metrics={},
            execution=ResultExecution(commit="0" * 40),
            sample={},
            inputs={},
            relations=[],
        )


def test_external_test_horizon_must_match_gate() -> None:
    graph = _repo_graph()
    test = graph.get(TEST_ID)
    nodes = dict(graph.nodes)
    nodes[TEST_ID] = test.model_copy(update={"horizon_years": 5})
    mismatched = KnowledgeGraph(nodes=nodes, repo_root=graph.repo_root)
    errors = validate_graph(mismatched)
    assert any("horizon_years 5 does not match" in error for error in errors)
