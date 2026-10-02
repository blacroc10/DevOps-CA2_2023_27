from app.evidence_graph import EvidenceGraphBuilder
from app.models import ClaimEvidence, ClaimVerdict, EvidenceSource, EvidenceNodeScore


def test_build_evidence_graph_with_stance_edges():
    builder = EvidenceGraphBuilder()
    claim_evidence = ClaimEvidence(
        claim="The Earth orbits the Sun.",
        evidence=[
            EvidenceSource(
                title="NASA",
                url="https://www.nasa.gov/solar-system",
                content="The Earth orbits the Sun.",
                score=0.9,
                reliability=5,
            )
        ],
    )
    verdict = ClaimVerdict(
        claim="The Earth orbits the Sun.",
        verdict="true",
        confidence=90,
        reasoning="NASA supports the claim.",
        supporting_sources=["https://www.nasa.gov/solar-system"],
    )
    node_scores = [
        EvidenceNodeScore(
            url="https://www.nasa.gov/solar-system",
            stance="support",
            authority=1.0,
            relevance=0.9,
            agreement=0.9,
            hop_distance=1,
            weight=0.81,
        )
    ]

    graph = builder.build(claim_evidence, verdict, node_scores)

    assert len(graph.nodes) == 2
    assert graph.nodes[1].type == "supporting_evidence"
    assert graph.edges[0].type == "supports"
    assert graph.edges[0].weight == 0.81

