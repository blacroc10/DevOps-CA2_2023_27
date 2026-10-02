import pytest

from app.models import ClaimExtractionResult, ClaimEvidence, ClaimVerdict, EvidenceSource, InputType
from app.pipeline import VerificationPipeline


class MockInputHandler:
    async def process(self, raw_input, input_type):
        from app.models import CleanedInput

        if input_type == InputType.url:
            return CleanedInput(input_type=InputType.url, text="Apollo 11 landed on the Moon in 1969.", source_url=raw_input)
        return CleanedInput(input_type=InputType.text, text=raw_input)


class MockClaimExtractor:
    async def extract(self, text):
        if "microchips" in text:
            return ClaimExtractionResult(claims=["Vaccines contain microchips."])
        return ClaimExtractionResult(claims=["Apollo 11 landed on the Moon in 1969."])


class MockEvidenceRetriever:
    async def retrieve_for_claims(self, claims):
        results = []
        for claim in claims:
            if "microchips" in claim:
                results.append(
                    ClaimEvidence(
                        claim=claim,
                        evidence=[EvidenceSource(url="https://www.cdc.gov/vaccines", content="Vaccines do not contain microchips.")],
                    )
                )
            else:
                results.append(
                    ClaimEvidence(
                        claim=claim,
                        evidence=[EvidenceSource(url="https://www.nasa.gov/apollo-11", content="Apollo 11 landed in 1969.")],
                    )
                )
        return results


class MockVerdictEngine:
    async def verify_claims(self, claim_evidence):
        from app.models import VerificationResponse

        verdicts = []
        for item in claim_evidence:
            if "microchips" in item.claim:
                verdicts.append(
                    ClaimVerdict(
                        claim=item.claim,
                        verdict="false",
                        confidence=91,
                        reasoning="CDC evidence contradicts the claim.",
                        contradicting_sources=["https://www.cdc.gov/vaccines"],
                    )
                )
            else:
                verdicts.append(
                    ClaimVerdict(
                        claim=item.claim,
                        verdict="true",
                        confidence=95,
                        reasoning="NASA evidence supports the claim.",
                        supporting_sources=["https://www.nasa.gov/apollo-11"],
                    )
                )
        return VerificationResponse(
            overall_verdict=verdicts[0].verdict,
            overall_confidence=verdicts[0].confidence,
            credibility_score=100 if verdicts[0].verdict == "true" else 0,
            claims=verdicts,
        )


def make_pipeline():
    return VerificationPipeline(
        input_handler=MockInputHandler(),
        claim_extractor=MockClaimExtractor(),
        evidence_retriever=MockEvidenceRetriever(),
        verdict_engine=MockVerdictEngine(),
    )


@pytest.mark.asyncio
async def test_full_pipeline_text_false_claim():
    response = await make_pipeline().verify("Vaccines contain microchips.", InputType.text)

    assert response.claims[0].verdict == "false"
    assert 0 <= response.claims[0].confidence <= 100


@pytest.mark.asyncio
async def test_full_pipeline_url_true_claim():
    response = await make_pipeline().verify("https://example.com/apollo", InputType.url)

    assert response.claims[0].verdict == "true"
    assert 0 <= response.claims[0].confidence <= 100

