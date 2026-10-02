import pytest

from app.config import Settings


@pytest.fixture
def test_settings() -> Settings:
    return Settings(
        _env_file=None,
        tavily_api_key="test-tavily",
        groq_api_key="test-groq",
        request_timeout_seconds=1,
        external_retry_count=0,
        retry_backoff_seconds=0,
    )
