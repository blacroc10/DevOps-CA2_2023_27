from app.models import AgentFinding, ClaimEvidence, ClaimEvidenceGraph, ClaimVerdict, EvidenceNodeScore


class MultiAgentReasoner:
    """Deterministic agent layer over the evidence graph.

    This keeps the backend predictable and testable while exposing the
    specialized-agent outputs shown in the architecture.
    """

    def analyze(
        self,
        claim_evidence: ClaimEvidence,
        verdict: ClaimVerdict,
        graph: ClaimEvidenceGraph,
        node_scores: list[EvidenceNodeScore],
    ) -> list[AgentFinding]:
        supporting = [node for node in node_scores if node.stance == "support"]
        contradicting = [node for node in node_scores if node.stance == "contradiction"]
        neutral = [node for node in node_scores if node.stance == "neutral"]
        avg_weight = sum(node.weight for node in node_scores) / len(node_scores) if node_scores else 0

        return [
            AgentFinding(
                agent="Evidence Analyzer Agent",
                summary=(
                    f"Reviewed {len(claim_evidence.evidence)} evidence passages; "
                    f"average cited-node weight is {avg_weight:.3f}."
                ),
                confidence=verdict.confidence,
            ),
            AgentFinding(
                agent="Contradiction Detector Agent",
                summary=f"Found {len(contradicting)} contradicting, {len(supporting)} supporting, and {len(neutral)} neutral evidence nodes.",
                confidence=verdict.confidence,
            ),
            AgentFinding(
                agent="Relationship Analyzer Agent",
                summary=f"Graph contains {len(graph.nodes)} nodes and {len(graph.edges)} edges, including evidence relationship edges when detected.",
                confidence=verdict.confidence,
            ),
            AgentFinding(
                agent="Confidence Estimator Agent",
                summary=f"Computed GraphTrust score R={verdict.graph_score} and confidence={verdict.graph_confidence}/100.",
                confidence=verdict.confidence,
            ),
            AgentFinding(
                agent="Summarizer Agent",
                summary=verdict.reasoning,
                confidence=verdict.confidence,
            ),
        ]
