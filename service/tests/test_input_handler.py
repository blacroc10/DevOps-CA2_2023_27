import httpx
import pytest

from app.input_handler import InputHandler
from app.models import InputType


@pytest.mark.asyncio
async def test_process_text_cleans_whitespace(test_settings):
    handler = InputHandler(test_settings)

    result = await handler.process("  NASA   landed Apollo 11\non the Moon. ", InputType.text)

    assert result.input_type == InputType.text
    assert result.text == "NASA landed Apollo 11 on the Moon."


@pytest.mark.asyncio
async def test_process_url_extracts_article_text(monkeypatch, test_settings):
    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return None

        async def get(self, url):
            request = httpx.Request("GET", url)
            return httpx.Response(200, request=request, text="<html><article><p>Article body about a fact.</p></article></html>")

    monkeypatch.setattr(httpx, "AsyncClient", MockClient)
    monkeypatch.setattr("app.input_handler.trafilatura.extract", lambda *args, **kwargs: "Article body about a fact.")

    handler = InputHandler(test_settings)
    result = await handler.process("https://example.com/story", InputType.url)

    assert result.input_type == InputType.url
    assert result.source_url == "https://example.com/story"
    assert result.text == "Article body about a fact."
