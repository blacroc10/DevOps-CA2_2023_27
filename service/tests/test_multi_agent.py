from app.multi_agent import MultiAgentReasoner
from app.models import (
    ClaimEvidence,
    ClaimEvidenceGraph,
    ClaimVerdict,
    EvidenceGraphEdge,
    EvidenceGraphNode,
    EvidenceNodeScore,
    EvidenceSource,
)


def test_multi_agent_reasoner_returns_specialized_findings():
    reasoner = MultiAgentReasoner()
    claim_evidence = ClaimEvidence(
        claim="The Earth orbits the Sun.",
        evidence=[EvidenceSource(url="https://www.nasa.gov/solar-system", content="Earth orbits the Sun.")],
    )
    verdict = ClaimVerdict(
        claim="The Earth orbits the Sun.",
        verdict="true",
        confidence=88,
        reasoning="Evidence supports the claim.",
        graph_score=0.8,
        graph_confidence=88,
        supporting_sources=["https://www.nasa.gov/solar-system"],
    )
    graph = ClaimEvidenceGraph(
        claim="The Earth orbits the Sun.",
        claim_node_id="claim_1",
        nodes=[
            EvidenceGraphNode(id="claim_1", type="claim", label="The Earth orbits the Sun."),
            EvidenceGraphNode(id="evidence_1", type="supporting_evidence", label="NASA"),
        ],
        edges=[EvidenceGraphEdge(source="evidence_1", target="claim_1", type="supports", weight=0.8)],
    )
    node_scores = [
        EvidenceNodeScore(
            url="https://www.nasa.gov/solar-system",
            stance="support",
            authority=1.0,
            relevance=0.9,
            agreement=0.88,
            hop_distance=1,
            weight=0.792,
        )
    ]

    findings = reasoner.analyze(claim_evidence, verdict, graph, node_scores)

    assert [finding.agent for finding in findings] == [
        "Evidence Analyzer Agent",
        "Contradiction Detector Agent",
        "Relationship Analyzer Agent",
        "Confidence Estimator Agent",
        "Summarizer Agent",
    ]

