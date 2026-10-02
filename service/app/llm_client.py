import json
import re
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.config import Settings, get_settings
from app.exceptions import ExternalServiceError, InvalidModelOutputError
from app.retry import with_retries

ModelT = TypeVar("ModelT", bound=BaseModel)


class LlamaClient:
    """Groq-hosted Llama client that returns validated Pydantic objects."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    async def complete_json(self, system_prompt: str, user_prompt: str, output_model: type[ModelT]) -> ModelT:
        if not self.settings.groq_api_key:
            raise ExternalServiceError("GROQ_API_KEY is not configured")

        async def operation() -> str | dict[str, Any]:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.post(
                    f"{self.settings.groq_base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.settings.groq_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.settings.llama_model,
                        "messages": [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0,
                        "response_format": {"type": "json_object"},
                    },
                )
                response.raise_for_status()
                payload = response.json()
                return payload["choices"][0]["message"]["content"]

        content = await with_retries(operation, self.settings, "Groq Llama request")
        return self._parse_content(content, output_model)

    @staticmethod
    def _parse_content(content: str | dict[str, Any], output_model: type[ModelT]) -> ModelT:
        try:
            if isinstance(content, str):
                return output_model.model_validate(LlamaClient._json_from_text(content))
            return output_model.model_validate(content)
        except (ValidationError, json.JSONDecodeError) as exc:
            raise InvalidModelOutputError(f"Malformed LLM JSON for {output_model.__name__}") from exc

    @staticmethod
    def _json_from_text(content: str) -> Any:
        cleaned = content.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
            if not match:
                raise
            return json.loads(match.group(0))
