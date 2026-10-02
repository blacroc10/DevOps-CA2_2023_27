import pytest

from app.models import ClaimEvidence, ClaimVerdict, EvidenceSource
from app.verdict_engine import VerdictEngine


class MockLLM:
    async def complete_json(self, system_prompt, user_prompt, output_model):
        if "microchips" in user_prompt:
            return ClaimVerdict(
                claim="Vaccines contain microchips.",
                verdict="false",
                confidence=94,
                reasoning="The cited CDC source contradicts this claim.",
                supporting_sources=[],
                contradicting_sources=["https://www.cdc.gov/vaccines"],
            )
        return ClaimVerdict(
            claim="Apollo 11 landed on the Moon in 1969.",
            verdict="true",
            confidence=96,
            reasoning="The cited NASA source supports the Apollo 11 landing date.",
            supporting_sources=["https://www.nasa.gov/apollo-11"],
            contradicting_sources=[],
        )

class MockGraphRepository:
    def __init__(self):
        self.saved = []

    def save_graph(self, graph):
        self.saved.append(graph)


@pytest.mark.asyncio
async def test_verify_claim_true_and_confidence_in_range(test_settings):
    engine = VerdictEngine(MockLLM(), test_settings)
    evidence = ClaimEvidence(
        claim="Apollo 11 landed on the Moon in 1969.",
        evidence=[EvidenceSource(url="https://www.nasa.gov/apollo-11", content="Apollo 11 landed in July 1969.")],
    )

    verdict = await engine.verify_claim(evidence)

    assert verdict.verdict == "true"
    assert 0 <= verdict.confidence <= 100


@pytest.mark.asyncio
async def test_verify_claim_false_and_confidence_in_range(test_settings):
    engine = VerdictEngine(MockLLM(), test_settings)
    evidence = ClaimEvidence(
        claim="Vaccines contain microchips.",
        evidence=[EvidenceSource(url="https://www.cdc.gov/vaccines", content="Vaccines do not contain microchips.")],
    )

    verdict = await engine.verify_claim(evidence)

    assert verdict.verdict == "false"
    assert 0 <= verdict.confidence <= 100


@pytest.mark.asyncio
async def test_verify_claims_returns_graph_and_agent_transparency(test_settings):
    repository = MockGraphRepository()
    engine = VerdictEngine(MockLLM(), test_settings, graph_repository=repository)
    evidence = ClaimEvidence(
        claim="Apollo 11 landed on the Moon in 1969.",
        evidence=[
            EvidenceSource(
                url="https://www.nasa.gov/apollo-11",
                content="Apollo 11 landed in July 1969.",
                score=0.9,
                reliability=5,
            )
        ],
    )

    response = await engine.verify_claims([evidence])

    assert response.evidence_graphs
    assert response.claims[0].evidence_nodes
    assert response.claims[0].agent_findings
    assert response.claims[0].graph_score is not None
    assert repository.saved == response.evidence_graphs


def test_aggregate_graphtrust_credibility(test_settings):
    engine = VerdictEngine(MockLLM(), test_settings)
    score = engine._credibility_score(
        [
            ClaimVerdict(
                claim="A",
                verdict="true",
                confidence=95,
                graph_confidence=95,
                reasoning="Supported.",
                supporting_sources=["https://example.com/a"],
            ),
            ClaimVerdict(
                claim="B",
                verdict="false",
                confidence=5,
                graph_confidence=5,
                reasoning="Contradicted.",
                contradicting_sources=["https://example.com/b"],
            ),
        ]
    )

    assert score == 50
