"""Generate deterministic knowledge-graph views."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from urban_growth.knowledge_graph.lifecycle import hypothesis_lifecycle, test_evaluation
from urban_growth.knowledge_graph.loader import load_graph
from urban_growth.knowledge_graph.models import NodeType
from urban_growth.knowledge_graph.validate import validate_graph


def render(root: Path) -> dict[str, str]:
    graph = load_graph(root / "nodes")
    errors = validate_graph(graph)
    if errors:
        raise ValueError("\n".join(errors))

    index = {
        node_id: {"type": node.type.value, "title": node.title}
        for node_id, node in sorted(graph.nodes.items())
    }
    status_lines = ["# Research status", ""]
    evidence_lines = ["# Evidence graph", ""]
    dependency_lines = ["# Dependency graph", ""]
    validation_lines = ["# Validation coverage", ""]

    for node in sorted(graph.nodes.values(), key=lambda item: item.id):
        if node.type == NodeType.hypothesis:
            status_lines.append(f"- `{node.id}` — **{hypothesis_lifecycle(graph, node.id)}** — {node.title}")
            for test_id in graph.targets(node.id, "tested_by"):
                evaluation = test_evaluation(graph, test_id)
                outcome = evaluation.outcome if evaluation else "pending"
                evidence_lines.append(f"- `{node.id}` → `{test_id}` → **{outcome}**")
                test = graph.get(test_id)
                validation_lines.append(f"- `{node.id}` / `{test.role.value}` / `{test_id}` — {outcome}")
        for relation, target in graph.outgoing(node.id):
            if relation in {"requires", "implemented_by", "blocked_by"}:
                dependency_lines.append(f"- `{node.id}` --{relation}--> `{target}`")

    return {
        "graph-index.json": json.dumps(index, indent=2, sort_keys=True) + "\n",
        "research-status.md": "\n".join(status_lines) + "\n",
        "evidence-graph.md": "\n".join(evidence_lines) + "\n",
        "dependency-graph.md": "\n".join(dependency_lines) + "\n",
        "validation-coverage.md": "\n".join(validation_lines) + "\n",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="knowledge")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(args.root)
    output_dir = root / "generated"
    outputs = render(root)
    if args.check:
        stale = [name for name, content in outputs.items() if not (output_dir / name).exists() or (output_dir / name).read_text(encoding="utf-8") != content]
        if stale:
            raise SystemExit(f"Generated knowledge-graph outputs are stale: {', '.join(stale)}")
        return
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        (output_dir / name).write_text(content, encoding="utf-8")


if __name__ == "__main__":
    main()
