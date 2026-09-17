"""Immutable in-memory graph representation and graph queries."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from urban_growth.knowledge_graph.models import Node


@dataclass(frozen=True)
class KnowledgeGraph:
    nodes: dict[str, Node]
    repo_root: Path

    def __post_init__(self) -> None:
        object.__setattr__(self, "_outgoing", self._build_outgoing())
        object.__setattr__(self, "_incoming", self._build_incoming())

    def _build_outgoing(self):
        result = defaultdict(list)
        for node in self.nodes.values():
            for rel in node.relations:
                result[(node.id, rel.type)].append(rel.target)
        return dict(result)

    def _build_incoming(self):
        result = defaultdict(list)
        for node in self.nodes.values():
            for rel in node.relations:
                result[(rel.target, rel.type)].append(node.id)
        return dict(result)

    def get(self, node_id: str) -> Node:
        return self.nodes[node_id]

    def targets(self, node_id: str, relation: str) -> list[str]:
        return list(self._outgoing.get((node_id, relation), []))

    def sources(self, node_id: str, relation: str) -> list[str]:
        return list(self._incoming.get((node_id, relation), []))

    def outgoing(self, node_id: str) -> list[tuple[str, str]]:
        return [
            (relation, target)
            for (source, relation), targets in self._outgoing.items()
            if source == node_id
            for target in targets
        ]

    def incoming(self, node_id: str) -> list[tuple[str, str]]:
        return [
            (relation, source)
            for (target, relation), sources in self._incoming.items()
            if target == node_id
            for source in sources
        ]
