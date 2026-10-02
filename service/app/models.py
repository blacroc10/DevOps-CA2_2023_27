from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


class InputType(str, Enum):
    text = "text"
    url = "url"


class CleanedInput(BaseModel):
    input_type: InputType
    text: str = Field(min_length=1)
    source_url: str | None = None


class VerifyRequest(BaseModel):
    input: str = Field(min_length=1)
    type: InputType


class ClaimExtractionResult(BaseModel):
    claims: list[str] = Field(default_factory=list, min_length=0, max_length=5)

    @field_validator("claims")
    @classmethod
    def strip_claims(cls, claims: list[str]) -> list[str]:
        return [claim.strip() for claim in claims if claim.strip()]


class EvidenceSource(BaseModel):
    title: str | None = None
    url: AnyHttpUrl
    content: str = Field(min_length=1)
    score: float | None = None
    reliability: int = 0
    source_type: Literal["web", "academic", "news", "trusted_database", "domain_specific"] = "web"


class ClaimEvidence(BaseModel):
    claim: str
    evidence: list[EvidenceSource] = Field(default_factory=list)


VerdictLabel = Literal["true", "false", "misleading", "unverifiable"]


class ClaimVerdict(BaseModel):
    claim: str
    verdict: VerdictLabel
    confidence: int = Field(ge=0, le=100)
    reasoning: str
    supporting_sources: list[str] = Field(default_factory=list)
    contradicting_sources: list[str] = Field(default_factory=list)
    graph_score: float | None = None
    graph_confidence: int | None = Field(default=None, ge=0, le=100)
    evidence_nodes: list[EvidenceNodeScore] = Field(default_factory=list)
    agent_findings: list[AgentFinding] = Field(default_factory=list)

    @field_validator("verdict", mode="before")
    @classmethod
    def normalize_verdict(cls, verdict: object) -> object:
        if isinstance(verdict, str):
            return verdict.strip().lower()
        return verdict

    @field_validator("confidence", mode="before")
    @classmethod
    def normalize_confidence(cls, confidence: object) -> object:
        if isinstance(confidence, str):
            value = confidence.strip().removesuffix("%")
            return round(float(value))
        if isinstance(confidence, float):
            return round(confidence)
        return confidence

    @field_validator("supporting_sources", "contradicting_sources", mode="before")
    @classmethod
    def normalize_sources(cls, sources: object) -> list[str]:
        if sources is None:
            return []
        if isinstance(sources, str):
            sources = [sources]
        normalized: list[str] = []
        if isinstance(sources, list):
            for source in sources:
                if isinstance(source, dict):
                    source = source.get("url") or source.get("source")
                if isinstance(source, str) and source.startswith(("http://", "https://")):
                    normalized.append(source)
        return normalized


class VerificationResponse(BaseModel):
    overall_verdict: VerdictLabel
    overall_confidence: int = Field(ge=0, le=100)
    credibility_score: int = Field(ge=0, le=100)
    claims: list[ClaimVerdict]
    evidence_graphs: list[ClaimEvidenceGraph] = Field(default_factory=list)


class EvidenceNodeScore(BaseModel):
    url: str
    stance: Literal["support", "contradiction", "neutral"]
    authority: float = Field(ge=0, le=1)
    relevance: float = Field(ge=0, le=1)
    agreement: float = Field(ge=0, le=1)
    hop_distance: int = Field(ge=1)
    weight: float = Field(ge=0)


GraphNodeType = Literal["claim", "supporting_evidence", "contradicting_evidence", "neutral_evidence"]
GraphEdgeType = Literal["supports", "contradicts", "refers_to", "similar_to"]


class EvidenceGraphNode(BaseModel):
    id: str
    type: GraphNodeType
    label: str
    url: str | None = None
    authority: float | None = Field(default=None, ge=0, le=1)
    relevance: float | None = Field(default=None, ge=0, le=1)
    agreement: float | None = Field(default=None, ge=0, le=1)
    weight: float | None = Field(default=None, ge=0)


class EvidenceGraphEdge(BaseModel):
    source: str
    target: str
    type: GraphEdgeType
    weight: float | None = Field(default=None, ge=0)


class ClaimEvidenceGraph(BaseModel):
    claim: str
    claim_node_id: str
    nodes: list[EvidenceGraphNode]
    edges: list[EvidenceGraphEdge]


class AgentFinding(BaseModel):
    agent: str
    summary: str
    confidence: int = Field(ge=0, le=100)


class ErrorResponse(BaseModel):
    detail: str
