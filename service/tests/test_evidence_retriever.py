import pytest

from app.evidence_retriever import EvidenceRetriever, domain_reliability, source_type


class MockTavilyClient:
    def search(self, **kwargs):
        return {
            "results": [
                {
                    "title": "Blog",
                    "url": "https://example.com/post",
                    "content": "A lower reliability source.",
                    "score": 0.99,
                },
                {
                    "title": "NASA",
                    "url": "https://www.nasa.gov/history/apollo-11",
                    "content": "NASA says Apollo 11 landed in 1969.",
                    "score": 0.5,
                },
            ]
        }


def test_domain_reliability_scores_known_domains():
    assert domain_reliability("https://www.nasa.gov/history") == 5
    assert domain_reliability("https://example.com") == 0


def test_source_type_classifies_evidence_domains():
    assert source_type("https://www.nasa.gov/history") == "trusted_database"
    assert source_type("https://www.reuters.com/world/story") == "news"
    assert source_type("https://example.edu/paper") == "academic"
    assert source_type("https://www.snopes.com/fact-check/story") == "domain_specific"
    assert source_type("https://example.com/post") == "web"


@pytest.mark.asyncio
async def test_retrieve_prioritizes_reliable_domains(test_settings):
    retriever = EvidenceRetriever(test_settings, MockTavilyClient())

    result = await retriever.retrieve("Apollo 11 landed in 1969")

    assert result.claim == "Apollo 11 landed in 1969"
    assert str(result.evidence[0].url) == "https://www.nasa.gov/history/apollo-11"
    assert result.evidence[0].reliability == 5
