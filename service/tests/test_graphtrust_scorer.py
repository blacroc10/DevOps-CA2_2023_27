from app.graphtrust_scorer import GraphTrustScorer, authority_score, sigmoid_confidence
from app.models import ClaimEvidence, ClaimVerdict, EvidenceSource


def test_authority_score_maps_source_tiers():
    assert authority_score(5) == 1.0
    assert authority_score(4) == 0.8
    assert authority_score(1) == 0.5
    assert authority_score(0) == 0.5
    assert authority_score(0, has_domain=False) == 0.2


def test_sigmoid_confidence_uses_k_and_raw_score():
    assert sigmoid_confidence(1.22, 2.5) == 95
    assert sigmoid_confidence(-1.22, 2.5) == 5


def test_score_claim_uses_authority_relevance_agreement_and_stance(test_settings):
    scorer = GraphTrustScorer(test_settings)
    claim_evidence = ClaimEvidence(
        claim="Apollo 11 landed on the Moon.",
        evidence=[
            EvidenceSource(
                url="https://www.nasa.gov/apollo-11",
                content="Apollo 11 landed on the Moon.",
                score=0.8,
                reliability=5,
            ),
            EvidenceSource(
                url="https://example.com/moon-hoax",
                content="Apollo 11 did not land on the Moon.",
                score=0.5,
                reliability=0,
            ),
        ],
    )
    verdict = ClaimVerdict(
        claim="Apollo 11 landed on the Moon.",
        verdict="true",
        confidence=90,
        reasoning="NASA supports the claim.",
        supporting_sources=["https://www.nasa.gov/apollo-11"],
        contradicting_sources=["https://example.com/moon-hoax"],
    )

    scored, nodes = scorer.score_claim(claim_evidence, verdict)

    assert nodes[0].weight == 0.72
    assert nodes[1].weight == 0.225
    assert scored.graph_score == 0.495
    assert scored.confidence == 78
    assert scored.verdict == "true"
