from urllib.parse import urlparse

import httpx
import trafilatura

from app.config import Settings, get_settings
from app.exceptions import ExternalServiceError
from app.models import CleanedInput, InputType
from app.retry import with_retries


def _clean_text(text: str) -> str:
    return " ".join(text.split())


def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


class InputHandler:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def process(self, raw_input: str, input_type: InputType) -> CleanedInput:
        if input_type == InputType.url:
            if not _looks_like_url(raw_input):
                raise ValueError("Input type is url, but input is not a valid http(s) URL")
            text = await self._extract_url_text(raw_input)
            return CleanedInput(input_type=InputType.url, text=text, source_url=raw_input)

        cleaned = _clean_text(raw_input)
        if not cleaned:
            raise ValueError("Input text is empty after cleaning")
        return CleanedInput(input_type=InputType.text, text=cleaned)

    async def _extract_url_text(self, url: str) -> str:
        async def operation() -> str:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds, follow_redirects=True) as client:
                response = await client.get(url)
                response.raise_for_status()
            extracted = trafilatura.extract(response.text, include_comments=False, include_tables=False)
            cleaned = _clean_text(extracted or "")
            if not cleaned:
                raise ExternalServiceError("Could not extract article text from URL")
            return cleaned

        return await with_retries(operation, self.settings, "URL extraction")

