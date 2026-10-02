from app.config import Settings, get_settings
from app.exceptions import InvalidModelOutputError
from app.llm_client import LlamaClient
from app.models import ClaimExtractionResult


SYSTEM_PROMPT = """You extract factual claims for verification.
Return strict JSON only, with schema {"claims": ["..."]}.
Extract 1 to 5 discrete, independently checkable factual claims.
Ignore opinions, predictions, jokes, and subjective language."""


class ClaimExtractor:
    def __init__(self, llm_client: LlamaClient | None = None, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.llm_client = llm_client or LlamaClient(self.settings)

    async def extract(self, text: str) -> ClaimExtractionResult:
        prompt = f"Text to analyze:\n{text}\n\nReturn only JSON."
        try:
            result = await self.llm_client.complete_json(SYSTEM_PROMPT, prompt, ClaimExtractionResult)
        except InvalidModelOutputError:
            retry_prompt = f"{prompt}\n\nYour prior answer was malformed. Return valid JSON with only a claims array."
            result = await self.llm_client.complete_json(SYSTEM_PROMPT, retry_prompt, ClaimExtractionResult)
        return ClaimExtractionResult(claims=result.claims[: self.settings.max_claims])

