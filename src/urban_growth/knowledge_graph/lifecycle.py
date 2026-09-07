"""Derived readiness, gate evaluation, and rule-driven hypothesis lifecycle computation."""

from __future__ import annotations

import operator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from urban_growth.knowledge_graph.graph import KnowledgeGraph
from urban_growth.knowledge_graph.models import (
    AcceptanceGateNode,
    ArtifactNode,
    ClaimScope,
    DatasetAvailability,
    DatasetNode,
    FailureInterpretation,
    HypothesisNode,
    ProvenanceState,
    ResultNode,
    TestRole,
    ValidationTestNode,
    VariableNode,
)

OPS = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt, "==": operator.eq}


@dataclass(frozen=True)
class GateEvaluation:
    gate_id: str
    outcome: str
    evaluated_metrics: dict[str, float]
    failure_interpretation: FailureInterpretation


def _load_lifecycle_rules(repo_root: Path) -> dict[str, Any]:
    path = repo_root / "knowledge" / "schema" / "lifecycle-rules.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "hypothesis" not in data or "test_disposition" not in data:
        raise ValueError(f"Invalid lifecycle rule file: {path}")
    return data


def artifact_ready(graph: KnowledgeGraph, artifact_id: str) -> bool:
    node = graph.get(artifact_id)
    return isinstance(node, ArtifactNode) and (graph.repo_root / node.path).is_file()


def dataset_ready(node: DatasetNode, rules: dict[str, Any]) -> bool:
    spec = rules["hypothesis"]["data_ready"]
    allowed_availability = {DatasetAvailability(item) for item in spec["requires_dataset_availability"]}
    allowed_provenance = {ProvenanceState(item) for item in spec["requires_provenance"]}
    return node.availability in allowed_availability and node.provenance in allowed_provenance


def variable_ready(
    graph: KnowledgeGraph,
    variable_id: str,
    rules: dict[str, Any] | None = None,
    stack: tuple[str, ...] = (),
) -> bool:
    if rules is None:
        rules = _load_lifecycle_rules(graph.repo_root)
    if variable_id in stack:
        raise ValueError(f"Variable dependency cycle: {' -> '.join((*stack, variable_id))}")
    node = graph.get(variable_id)
    allowed_provenance = {
        ProvenanceState(item)
        for item in rules["hypothesis"]["data_ready"]["requires_provenance"]
    }
    if not isinstance(node, VariableNode) or node.provenance not in allowed_provenance:
        return False
    if node.raw_source:
        datasets = graph.targets(variable_id, "derived_from")
        return (
            bool(datasets)
            and node.field_mapping_documented
            and all(
                isinstance(graph.get(item), DatasetNode) and dataset_ready(graph.get(item), rules)
                for item in datasets
            )
        )
    artifacts = graph.targets(variable_id, "produced_by")
    if not artifacts or not all(artifact_ready(graph, item) for item in artifacts):
        return False
    datasets = [
        item
        for item in graph.targets(variable_id, "derived_from")
        if isinstance(graph.get(item), DatasetNode)
    ]
    if not all(dataset_ready(graph.get(item), rules) for item in datasets):
        return False
    upstream = [
        item
        for item in graph.targets(variable_id, "requires")
        if isinstance(graph.get(item), VariableNode)
    ]
    return all(variable_ready(graph, item, rules, (*stack, variable_id)) for item in upstream)


def evaluate_gate(result: ResultNode, gate: AcceptanceGateNode) -> GateEvaluation:
    if result.status != "completed":
        return GateEvaluation(gate.id, "inconclusive", {}, gate.failure_interpretation)
    evaluated = {}
    for condition in gate.conditions:
        if condition.metric not in result.metrics:
            return GateEvaluation(gate.id, "inconclusive", evaluated, gate.failure_interpretation)
        value = result.metrics[condition.metric]
        evaluated[condition.metric] = value
        if not OPS[condition.operator](value, condition.threshold):
            return GateEvaluation(gate.id, "fail", evaluated, gate.failure_interpretation)
    return GateEvaluation(gate.id, "pass", evaluated, gate.failure_interpretation)


def test_evaluation(graph: KnowledgeGraph, test_id: str) -> GateEvaluation | None:
    test = graph.get(test_id)
    if not isinstance(test, ValidationTestNode):
        raise TypeError(f"{test_id} is not a validation test")
    gate_ids = graph.targets(test_id, "judged_by")
    if len(gate_ids) != 1:
        return None
    gate = graph.get(gate_ids[0])
    if not isinstance(gate, AcceptanceGateNode):
        return None
    results = [graph.get(item) for item in graph.targets(test_id, "produces")]
    results = [item for item in results if isinstance(item, ResultNode)]
    if not results:
        return None
    return evaluate_gate(max(results, key=lambda item: item.executed_at), gate)


def _required_roles(rules: dict[str, Any], transition: str, scope: ClaimScope) -> set[TestRole]:
    raw = rules["hypothesis"].get(transition, {}).get("required_test_roles", {})
    if isinstance(raw, list):
        return {TestRole(item) for item in raw}
    return {TestRole(item) for item in raw.get(scope.value, [])}


def _tests_for_roles(
    graph: KnowledgeGraph,
    hypothesis_id: str,
    roles: set[TestRole],
) -> list[str]:
    return [
        test_id
        for test_id in graph.targets(hypothesis_id, "tested_by")
        if isinstance(graph.get(test_id), ValidationTestNode) and graph.get(test_id).role in roles
    ]


def transition_test_disposition(
    graph: KnowledgeGraph,
    hypothesis_id: str,
    test_id: str,
    transition: str,
) -> str:
    """Classify one test for one hypothesis transition using the v1 R4 rules.

    A failure is blocking only when the test role is required for the transition and the
    gate's failure interpretation is blocking for the evaluated hypothesis claim scope.
    Failures outside that scope are diagnostics. Missing/invalid results remain
    inconclusive and can never be silently promoted to blocking failures.
    """
    rules = _load_lifecycle_rules(graph.repo_root)
    hypothesis = graph.get(hypothesis_id)
    test = graph.get(test_id)
    if not isinstance(hypothesis, HypothesisNode):
        raise TypeError(f"{hypothesis_id} is not a hypothesis")
    if not isinstance(test, ValidationTestNode):
        raise TypeError(f"{test_id} is not a validation test")

    evaluation = test_evaluation(graph, test_id)
    if evaluation is None:
        return "inconclusive"
    if evaluation.outcome == "pass":
        required = test.role in _required_roles(rules, transition, hypothesis.claim_scope)
        return "pass" if required else "diagnostic"
    if evaluation.outcome == "inconclusive":
        return "inconclusive"

    required = test.role in _required_roles(rules, transition, hypothesis.claim_scope)
    if not required:
        return "diagnostic"
    fail_rules = rules["test_disposition"]["fail"]
    failure_rule = fail_rules[evaluation.failure_interpretation.value]
    blocking_scopes = {ClaimScope(item) for item in failure_rule["blocking_claim_scopes"]}
    if hypothesis.claim_scope in blocking_scopes:
        return "blocking_failure"
    return failure_rule["otherwise"]


def _specified(graph: KnowledgeGraph, hypothesis: HypothesisNode, rules: dict[str, Any]) -> bool:
    spec = rules["hypothesis"]["specified"]
    if hypothesis.claim_scope == ClaimScope.primary:
        required_roles = {TestRole.primary_falsification}
    else:
        required_roles = {TestRole.supporting}
    tests = _tests_for_roles(graph, hypothesis.id, required_roles)
    if spec.get("requires_primary_falsification_test") and not tests:
        return False
    return not (
        spec.get("requires_acceptance_gate")
        and any(len(graph.targets(test_id, "judged_by")) != 1 for test_id in tests)
    )


def _data_ready(
    graph: KnowledgeGraph,
    hypothesis: HypothesisNode,
    rules: dict[str, Any],
) -> bool:
    for node_id in graph.targets(hypothesis.id, "requires"):
        node = graph.get(node_id)
        if isinstance(node, DatasetNode) and not dataset_ready(node, rules):
            return False
        if isinstance(node, VariableNode) and not variable_ready(graph, node_id, rules):
            return False
    return True


def _implemented(graph: KnowledgeGraph, hypothesis: HypothesisNode, rules: dict[str, Any]) -> bool:
    spec = rules["hypothesis"]["implemented"]
    if not spec.get("requires_repository_artifact"):
        return True
    artifacts = [
        item
        for item in graph.targets(hypothesis.id, "implemented_by")
        if isinstance(graph.get(item), ArtifactNode)
    ]
    return bool(artifacts) and all(artifact_ready(graph, item) for item in artifacts)


def _test_transition_satisfied(
    graph: KnowledgeGraph,
    hypothesis: HypothesisNode,
    transition: str,
    rules: dict[str, Any],
) -> bool | None:
    roles = _required_roles(rules, transition, hypothesis.claim_scope)
    if not roles:
        return None
    tests = _tests_for_roles(graph, hypothesis.id, roles)
    if not tests:
        return None
    dispositions = [
        transition_test_disposition(graph, hypothesis.id, test_id, transition) for test_id in tests
    ]
    return all(item == "pass" for item in dispositions)


def hypothesis_lifecycle(graph: KnowledgeGraph, hypothesis_id: str) -> str:
    rules = _load_lifecycle_rules(graph.repo_root)
    hypothesis = graph.get(hypothesis_id)
    if not isinstance(hypothesis, HypothesisNode):
        raise TypeError(f"{hypothesis_id} is not a hypothesis")
    if not _specified(graph, hypothesis, rules):
        return "unspecified"

    state = "specified"
    if not _data_ready(graph, hypothesis, rules):
        return state
    state = "data_ready"
    if not _implemented(graph, hypothesis, rules):
        return state
    state = "implemented"

    for transition in ("internally_validated", "externally_validated", "evidence_supported"):
        satisfied = _test_transition_satisfied(graph, hypothesis, transition, rules)
        if satisfied is None:
            continue
        if not satisfied:
            return state
        state = transition

    publication = rules["hypothesis"].get("publication_ready", {})
    if publication.get("enabled"):
        raise NotImplementedError("publication_ready checks must be specified before enabling")
    return state
