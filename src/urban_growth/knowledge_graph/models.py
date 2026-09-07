"""Pydantic models for the version-controlled research knowledge graph."""
from __future__ import annotations
from enum import Enum
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
class NodeType(str,Enum):
    research_question="research_question"; hypothesis="hypothesis"; dataset="dataset"; variable="variable"; artifact="artifact"; validation_test="validation_test"; acceptance_gate="acceptance_gate"; result="result"; finding="finding"; limitation="limitation"; github_issue="github_issue"
class DatasetAvailability(str,Enum):
    unregistered="unregistered"; registered="registered"; accessible="accessible"; ingested="ingested"; validated="validated"; unavailable="unavailable"
class ProvenanceState(str,Enum):
    missing="missing"; partial="partial"; documented="documented"; verified="verified"
class TestRole(str,Enum):
    primary_falsification="primary_falsification"; supporting="supporting"; internal_validation="internal_validation"; external_validation="external_validation"; sensitivity="sensitivity"; diagnostic="diagnostic"
class FailureInterpretation(str,Enum):
    falsifies_primary_claim="falsifies_primary_claim"; contradicts_supporting_claim="contradicts_supporting_claim"; weakens_evidence="weakens_evidence"; inconclusive="inconclusive"; diagnostic_only="diagnostic_only"
class Relation(BaseModel):
    model_config=ConfigDict(extra="forbid")
    type:str; target:str
class Node(BaseModel):
    model_config=ConfigDict(extra="allow")
    id:str; type:NodeType; title:str; canonical_name:str; aliases:list[str]=Field(default_factory=list); relations:list[Relation]=Field(default_factory=list)
class HypothesisNode(Node):
    model_config=ConfigDict(extra="forbid")
    type:Literal[NodeType.hypothesis]
class DatasetNode(Node):
    model_config=ConfigDict(extra="forbid")
    type:Literal[NodeType.dataset]; availability:DatasetAvailability; provenance:ProvenanceState; source:str; vintage:str|None=None; relations:list[Relation]=Field(default_factory=list)
class VariableNode(Node):
    model_config=ConfigDict(extra="forbid")
    type:Literal[NodeType.variable]; provenance:ProvenanceState; field_mapping_documented:bool=False; raw_source:bool=False; relations:list[Relation]=Field(default_factory=list)
class ArtifactNode(Node):
    model_config=ConfigDict(extra="forbid")
    type:Literal[NodeType.artifact]; path:str; relations:list[Relation]=Field(default_factory=list)
class ValidationTestNode(Node):
    model_config=ConfigDict(extra="forbid")
    type:Literal[NodeType.validation_test]; role:TestRole; relations:list[Relation]=Field(default_factory=list)
class GateCondition(BaseModel):
    model_config=ConfigDict(extra="forbid")
    metric:str; operator:Literal[">=",">","<=","<","=="]; threshold:float
class AcceptanceGateNode(Node):
    model_config=ConfigDict(extra="forbid")
    type:Literal[NodeType.acceptance_gate]; conditions:list[GateCondition]; failure_interpretation:FailureInterpretation; relations:list[Relation]=Field(default_factory=list)
class ResultExecution(BaseModel):
    model_config=ConfigDict(extra="forbid")
    commit:str; environment_lock:str|None=None; command:str|None=None; random_seed:int|None=None
class ResultNode(Node):
    model_config=ConfigDict(extra="forbid")
    type:Literal[NodeType.result]; test:str; status:Literal["completed","error","invalid"]; executed_at:str; metrics:dict[str,float]=Field(default_factory=dict); execution:ResultExecution; sample:dict[str,Any]=Field(default_factory=dict); inputs:dict[str,list[str]]=Field(default_factory=dict); relations:list[Relation]=Field(default_factory=list)
    @model_validator(mode="before")
    @classmethod
    def prohibit_derived_fields(cls,data:Any)->Any:
        if isinstance(data,dict) and "gate_evaluation" in data: raise ValueError("gate_evaluation is derived and may not be stored in result YAML")
        if isinstance(data,dict) and data.get("outcome") in {"pass","fail","inconclusive"}: raise ValueError("scientific outcome is derived from the acceptance gate")
        return data
_SPECIALIZED={NodeType.hypothesis:HypothesisNode,NodeType.dataset:DatasetNode,NodeType.variable:VariableNode,NodeType.artifact:ArtifactNode,NodeType.validation_test:ValidationTestNode,NodeType.acceptance_gate:AcceptanceGateNode,NodeType.result:ResultNode}
def parse_node(data:dict[str,Any])->Node:
    node_type=NodeType(data["type"]); return _SPECIALIZED.get(node_type,Node).model_validate(data)
