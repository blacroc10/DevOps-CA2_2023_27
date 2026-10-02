class TruthEngineError(Exception):
    """Base exception for user-facing verification failures."""


class ExternalServiceError(TruthEngineError):
    """Raised when Tavily, Groq, or page extraction fails after retries."""


class InvalidModelOutputError(TruthEngineError):
    """Raised when an LLM response cannot be parsed into the expected schema."""

