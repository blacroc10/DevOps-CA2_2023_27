import hashlib

from app.models import (
    ClaimEvidence,
    ClaimEvidenceGraph,
    ClaimVerdict,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    EvidenceNodeScore,
)
from app.relationship_detector import RelationshipDetector


def stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return f"{prefix}_{digest}"


class EvidenceGraphBuilder:
    def __init__(self, relationship_detector: RelationshipDetector | None = None) -> None:
        self.relationship_detector = relationship_detector or RelationshipDetector()

    def build(
        self,
        claim_evidence: ClaimEvidence,
        verdict: ClaimVerdict,
        node_scores: list[EvidenceNodeScore],
    ) -> ClaimEvidenceGraph:
        claim_node_id = stable_id("claim", claim_evidence.claim)
        score_by_url = {score.url: score for score in node_scores}
        nodes: list[EvidenceGraphNode] = [
            EvidenceGraphNode(id=claim_node_id, type="claim", label=claim_evidence.claim)
        ]
        edges: list[EvidenceGraphEdge] = []
        evidence_node_ids: list[str] = []

        for source in claim_evidence.evidence:
            url = str(source.url)
            score = score_by_url[url]
            evidence_node_id = stable_id("evidence", url)
            evidence_node_ids.append(evidence_node_id)
            node_type = self._node_type(score.stance)
            nodes.append(
                EvidenceGraphNode(
                    id=evidence_node_id,
                    type=node_type,
                    label=source.title or url,
                    url=url,
                    authority=score.authority,
                    relevance=score.relevance,
                    agreement=score.agreement,
                    weight=score.weight,
                )
            )
            edges.append(
                EvidenceGraphEdge(
                    source=evidence_node_id,
                    target=claim_node_id,
                    type=self._edge_type(score.stance),
                    weight=score.weight,
                )
            )

        edges.extend(self.relationship_detector.similar_evidence_edges(claim_evidence.evidence, evidence_node_ids))
        return ClaimEvidenceGraph(claim=claim_evidence.claim, claim_node_id=claim_node_id, nodes=nodes, edges=edges)

    @staticmethod
    def _node_type(stance: str) -> str:
        if stance == "support":
            return "supporting_evidence"
        if stance == "contradiction":
            return "contradicting_evidence"
        return "neutral_evidence"

    @staticmethod
    def _edge_type(stance: str) -> str:
        if stance == "support":
            return "supports"
        if stance == "contradiction":
            return "contradicts"
        return "refers_to"
