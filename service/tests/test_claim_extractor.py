import pytest

from app.claim_extractor import ClaimExtractor
from app.exceptions import InvalidModelOutputError
from app.models import ClaimExtractionResult


class MockLLM:
    def __init__(self):
        self.calls = 0

    async def complete_json(self, system_prompt, user_prompt, output_model):
        self.calls += 1
        return ClaimExtractionResult(claims=["The Earth orbits the Sun.", "Vaccines contain microchips."])


class RetryLLM:
    def __init__(self):
        self.calls = 0

    async def complete_json(self, system_prompt, user_prompt, output_model):
        self.calls += 1
        if self.calls == 1:
            raise InvalidModelOutputError("bad json")
        return ClaimExtractionResult(claims=["Apollo 11 landed on the Moon in 1969."])


@pytest.mark.asyncio
async def test_extract_claims(test_settings):
    llm = MockLLM()
    extractor = ClaimExtractor(llm, test_settings)

    result = await extractor.extract("Some text")

    assert result.claims == ["The Earth orbits the Sun.", "Vaccines contain microchips."]


@pytest.mark.asyncio
async def test_extract_retries_once_on_bad_json(test_settings):
    llm = RetryLLM()
    extractor = ClaimExtractor(llm, test_settings)

    result = await extractor.extract("Some text")

    assert llm.calls == 2
    assert result.claims == ["Apollo 11 landed on the Moon in 1969."]

