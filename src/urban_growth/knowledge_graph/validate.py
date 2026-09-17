"""Semantic validation for knowledge graph topology and governance invariants."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import yaml

from urban_growth.knowledge_graph.graph import KnowledgeGraph
from urban_growth.knowledge_graph.models import (
    AcceptanceGateNode,
    ClaimScope,
    GeographyNode,
    HypothesisNode,
    NodeType,
    ResultNode,
    ValidationTestNode,
    ValidationType,
)


def _load_relation_constraints(repo_root: Path):
    path = repo_root / "knowledge" / "schema" / "relation-types.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    result = {}
    for name, spec in data["relations"].items():
        result[name] = (
            {NodeType(item) for item in spec["sources"]},
            {NodeType(item) for item in spec["targets"]},
        )
    return result


def validate_graph(graph: KnowledgeGraph) -> list[str]:
    errors = []
    canonical = defaultdict(list)
    aliases = defaultdict(list)
    constraints = _load_relation_constraints(graph.repo_root)
    for node in graph.nodes.values():
        canonical[(node.type, node.canonical_name.strip().casefold())].append(node.id)
        for alias in node.aliases:
            aliases[(node.type, alias.strip().casefold())].append(node.id)
        for rel in node.relations:
            if rel.target not in graph.nodes:
                errors.append(f"{node.id}: relation {rel.type} targets missing node {rel.target}")
                continue
            if rel.type not in constraints:
                errors.append(f"{node.id}: unknown relation type {rel.type}")
                continue
            allowed_sources, allowed_targets = constraints[rel.type]
            target = graph.get(rel.target)
            if node.type not in allowed_sources or target.type not in allowed_targets:
                errors.append(f"{node.id}: illegal {rel.type} edge to {target.id}")
            if rel.type == "has_supporting_claim" and (
                not isinstance(target, HypothesisNode) or target.claim_scope != ClaimScope.supporting
            ):
                errors.append(f"{node.id}: has_supporting_claim target {target.id} must be supporting")
    for key, ids in canonical.items():
        if len(ids) > 1:
            errors.append(f"Duplicate canonical identity {key}: {sorted(ids)}")
    for key, ids in aliases.items():
        if len(set(ids)) > 1:
            errors.append(f"Duplicate alias identity {key}: {sorted(set(ids))}")
    for node in graph.nodes.values():
        if (
            node.type == NodeType.hypothesis
            and not graph.targets(node.id, "tested_by")
            and not graph.targets(node.id, "has_supporting_claim")
        ):
            errors.append(f"{node.id}: hypothesis has no validation test")
        if isinstance(node, HypothesisNode) and node.claim_scope == ClaimScope.supporting:
            parents = graph.sources(node.id, "has_supporting_claim")
            if len(parents) != 1:
                errors.append(f"{node.id}: supporting claim must have exactly one parent hypothesis")
        if isinstance(node, ValidationTestNode):
            gate_ids = graph.targets(node.id, "judged_by")
            if len(gate_ids) != 1:
                errors.append(f"{node.id}: validation test must have exactly one acceptance gate")
            elif isinstance(graph.get(gate_ids[0]), AcceptanceGateNode):
                gate = graph.get(gate_ids[0])
                if (
                    node.horizon_years is not None
                    and gate.horizon_years is not None
                    and node.horizon_years != gate.horizon_years
                ):
                    errors.append(
                        f"{node.id}: horizon_years {node.horizon_years} does not match "
                        f"{gate.id} horizon_years {gate.horizon_years}"
                    )
        if isinstance(node, ResultNode):
            if node.test not in graph.nodes:
                errors.append(f"{node.id}: result.test targets missing node {node.test}")
            elif node.id not in graph.targets(node.test, "produces"):
                errors.append(
                    f"{node.id}: result must be linked by {node.test} --produces--> {node.id}"
                )
            if node.validation_type == ValidationType.direct_count_external:
                geography = graph.get(node.geography) if node.geography in graph.nodes else None
                if not isinstance(geography, GeographyNode):
                    errors.append(
                        f"{node.id}: direct_count_external geography must reference geography node"
                    )
                elif node.geography not in graph.targets(node.test, "validated_in"):
                    errors.append(
                        f"{node.id}: geography {node.geography} must match {node.test} validated_in"
                    )
    _validate_variable_cycles(graph, errors)
    return errors


def _validate_variable_cycles(graph: KnowledgeGraph, errors: list[str]) -> None:
    visiting = set()
    visited = set()

    def visit(node_id, path):
        if node_id in visiting:
            errors.append(f"Variable dependency cycle: {' -> '.join((*path, node_id))}")
            return
        if node_id in visited:
            return
        visiting.add(node_id)
        node = graph.get(node_id)
        if node.type == NodeType.variable:
            for target in graph.targets(node_id, "requires"):
                if graph.get(target).type == NodeType.variable:
                    visit(target, [*path, node_id])
        visiting.remove(node_id)
        visited.add(node_id)

    for node in graph.nodes.values():
        if node.type == NodeType.variable:
            visit(node.id, [])
