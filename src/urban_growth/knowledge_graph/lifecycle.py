"""Derived readiness, gate evaluation, and hypothesis lifecycle computation."""
from __future__ import annotations
import operator
from dataclasses import dataclass
from urban_growth.knowledge_graph.graph import KnowledgeGraph
from urban_growth.knowledge_graph.models import AcceptanceGateNode,DatasetAvailability,DatasetNode,FailureInterpretation,ProvenanceState,ResultNode,TestRole,ValidationTestNode,VariableNode,ArtifactNode
OPS={">=":operator.ge,">":operator.gt,"<=":operator.le,"<":operator.lt,"==":operator.eq}
READY_DATASET_AVAILABILITY={DatasetAvailability.ingested,DatasetAvailability.validated}
READY_PROVENANCE={ProvenanceState.documented,ProvenanceState.verified}
BLOCKING_FAILURES={FailureInterpretation.falsifies_primary_claim,FailureInterpretation.contradicts_supporting_claim}
@dataclass(frozen=True)
class GateEvaluation:
    gate_id:str; outcome:str; evaluated_metrics:dict[str,float]; failure_interpretation:FailureInterpretation

def artifact_ready(graph:KnowledgeGraph,artifact_id:str)->bool:
    node=graph.get(artifact_id)
    return isinstance(node,ArtifactNode) and (graph.repo_root/node.path).is_file()

def dataset_ready(node:DatasetNode)->bool:
    return node.availability in READY_DATASET_AVAILABILITY and node.provenance in READY_PROVENANCE

def variable_ready(graph:KnowledgeGraph,variable_id:str,stack:tuple[str,...]=())->bool:
    if variable_id in stack: raise ValueError(f"Variable dependency cycle: {' -> '.join((*stack,variable_id))}")
    node=graph.get(variable_id)
    if not isinstance(node,VariableNode) or node.provenance not in READY_PROVENANCE:return False
    if node.raw_source:
        datasets=graph.targets(variable_id,"derived_from")
        return bool(datasets) and node.field_mapping_documented and all(isinstance(graph.get(item),DatasetNode) and dataset_ready(graph.get(item)) for item in datasets)
    artifacts=graph.targets(variable_id,"produced_by")
    if not artifacts or not all(artifact_ready(graph,item) for item in artifacts):return False
    datasets=[item for item in graph.targets(variable_id,"derived_from") if isinstance(graph.get(item),DatasetNode)]
    if not all(dataset_ready(graph.get(item)) for item in datasets):return False
    upstream=[item for item in graph.targets(variable_id,"requires") if isinstance(graph.get(item),VariableNode)]
    return all(variable_ready(graph,item,(*stack,variable_id)) for item in upstream)

def evaluate_gate(result:ResultNode,gate:AcceptanceGateNode)->GateEvaluation:
    if result.status!="completed":return GateEvaluation(gate.id,"inconclusive",{},gate.failure_interpretation)
    evaluated={}
    for condition in gate.conditions:
        if condition.metric not in result.metrics:return GateEvaluation(gate.id,"inconclusive",evaluated,gate.failure_interpretation)
        value=result.metrics[condition.metric];evaluated[condition.metric]=value
        if not OPS[condition.operator](value,condition.threshold):return GateEvaluation(gate.id,"fail",evaluated,gate.failure_interpretation)
    return GateEvaluation(gate.id,"pass",evaluated,gate.failure_interpretation)

def test_evaluation(graph:KnowledgeGraph,test_id:str)->GateEvaluation|None:
    test=graph.get(test_id)
    if not isinstance(test,ValidationTestNode):raise TypeError(f"{test_id} is not a validation test")
    gate_ids=graph.targets(test_id,"judged_by")
    if len(gate_ids)!=1:return None
    gate=graph.get(gate_ids[0])
    if not isinstance(gate,AcceptanceGateNode):return None
    results=[graph.get(item) for item in graph.targets(test_id,"produces")]
    results=[item for item in results if isinstance(item,ResultNode)]
    if not results:return None
    return evaluate_gate(max(results,key=lambda item:item.executed_at),gate)

def _tests_for_role(graph:KnowledgeGraph,hypothesis_id:str,role:TestRole)->list[str]:
    return [test_id for test_id in graph.targets(hypothesis_id,"tested_by") if isinstance(graph.get(test_id),ValidationTestNode) and graph.get(test_id).role==role]

def _role_satisfied(graph:KnowledgeGraph,hypothesis_id:str,role:TestRole)->bool:
    tests=_tests_for_role(graph,hypothesis_id,role)
    return bool(tests) and all((ev:=test_evaluation(graph,test_id)) is not None and ev.outcome=="pass" for test_id in tests)

def hypothesis_lifecycle(graph:KnowledgeGraph,hypothesis_id:str)->str:
    hypothesis=graph.get(hypothesis_id)
    if hypothesis.type.value!="hypothesis":raise TypeError(f"{hypothesis_id} is not a hypothesis")
    primary=_tests_for_role(graph,hypothesis_id,TestRole.primary_falsification)
    if not primary or any(len(graph.targets(test_id,"judged_by"))!=1 for test_id in primary):return "unspecified"
    state="specified"
    for node_id in graph.targets(hypothesis_id,"requires"):
        node=graph.get(node_id)
        if isinstance(node,DatasetNode) and not dataset_ready(node):return state
        if isinstance(node,VariableNode) and not variable_ready(graph,node_id):return state
    state="data_ready"
    artifacts=[item for item in graph.targets(hypothesis_id,"implemented_by") if isinstance(graph.get(item),ArtifactNode)]
    if not artifacts or not all(artifact_ready(graph,item) for item in artifacts):return state
    state="implemented"
    internal=_tests_for_role(graph,hypothesis_id,TestRole.internal_validation)
    if internal:
        if not _role_satisfied(graph,hypothesis_id,TestRole.internal_validation):return state
        state="internally_validated"
    external=_tests_for_role(graph,hypothesis_id,TestRole.external_validation)
    if external:
        if not _role_satisfied(graph,hypothesis_id,TestRole.external_validation):return state
        state="externally_validated"
    primary_evaluations=[test_evaluation(graph,test_id) for test_id in primary]
    if not all(item is not None and item.outcome=="pass" for item in primary_evaluations):return state
    return "evidence_supported"
