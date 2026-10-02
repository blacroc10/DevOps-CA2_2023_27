from app.claim_extractor import ClaimExtractor
from app.evidence_retriever import EvidenceRetriever
from app.input_handler import InputHandler
from app.models import InputType, VerificationResponse
from app.verdict_engine import VerdictEngine


class VerificationPipeline:
    def __init__(
        self,
        input_handler: InputHandler | None = None,
        claim_extractor: ClaimExtractor | None = None,
        evidence_retriever: EvidenceRetriever | None = None,
        verdict_engine: VerdictEngine | None = None,
    ) -> None:
        self.input_handler = input_handler or InputHandler()
        self.claim_extractor = claim_extractor or ClaimExtractor()
        self.evidence_retriever = evidence_retriever or EvidenceRetriever()
        self.verdict_engine = verdict_engine or VerdictEngine()

    async def verify(self, raw_input: str, input_type: InputType) -> VerificationResponse:
        cleaned = await self.input_handler.process(raw_input, input_type)
        extracted = await self.claim_extractor.extract(cleaned.text)
        if not extracted.claims:
            return VerificationResponse(
                overall_verdict="unverifiable",
                overall_confidence=0,
                credibility_score=50,
                claims=[],
            )
        claim_evidence = await self.evidence_retriever.retrieve_for_claims(extracted.claims)
        return await self.verdict_engine.verify_claims(claim_evidence)
