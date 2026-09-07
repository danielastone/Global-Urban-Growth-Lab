"""Load graph YAML files through Pydantic into a KnowledgeGraph."""
from __future__ import annotations
from pathlib import Path
import yaml
from urban_growth.knowledge_graph.graph import KnowledgeGraph
from urban_growth.knowledge_graph.models import parse_node

def load_graph(root:str|Path)->KnowledgeGraph:
    root_path=Path(root)
    nodes={}
    for path in sorted(root_path.rglob("*.yaml")):
        data=yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data,dict): raise ValueError(f"Knowledge graph node must be a mapping: {path}")
        node=parse_node(data)
        if node.id in nodes: raise ValueError(f"Duplicate node id {node.id}: {path}")
        nodes[node.id]=node
    return KnowledgeGraph(nodes=nodes,repo_root=root_path.parent.parent)
