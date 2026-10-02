from urllib.parse import urlparse

from tavily import TavilyClient

from app.config import Settings, get_settings
from app.exceptions import ExternalServiceError
from app.models import ClaimEvidence, EvidenceSource
from app.retry import with_retries


HIGH_RELIABILITY_DOMAINS = {
    "apnews.com": 5,
    "reuters.com": 5,
    "bbc.com": 4,
    "bbc.co.uk": 4,
    "npr.org": 4,
    "who.int": 5,
    "cdc.gov": 5,
    "nih.gov": 5,
    "nasa.gov": 5,
    "noaa.gov": 5,
    "un.org": 5,
    "worldbank.org": 4,
    "factcheck.org": 5,
    "politifact.com": 5,
    "snopes.com": 4,
}

ACADEMIC_DOMAINS = {"edu", "arxiv.org", "pubmed.ncbi.nlm.nih.gov", "scholar.google.com", "semanticscholar.org"}
NEWS_DOMAINS = {"apnews.com", "reuters.com", "bbc.com", "bbc.co.uk", "npr.org", "nytimes.com", "theguardian.com"}
TRUSTED_DATABASE_DOMAINS = {"who.int", "cdc.gov", "nih.gov", "nasa.gov", "noaa.gov", "un.org", "worldbank.org"}
DOMAIN_SPECIFIC_DOMAINS = {"factcheck.org", "politifact.com", "snopes.com"}


def domain_reliability(url: str) -> int:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    return max((score for domain, score in HIGH_RELIABILITY_DOMAINS.items() if host == domain or host.endswith(f".{domain}")), default=0)


def source_type(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if host.endswith(".edu") or any(host == domain or host.endswith(f".{domain}") for domain in ACADEMIC_DOMAINS):
        return "academic"
    if any(host == domain or host.endswith(f".{domain}") for domain in TRUSTED_DATABASE_DOMAINS):
        return "trusted_database"
    if any(host == domain or host.endswith(f".{domain}") for domain in DOMAIN_SPECIFIC_DOMAINS):
        return "domain_specific"
    if any(host == domain or host.endswith(f".{domain}") for domain in NEWS_DOMAINS):
        return "news"
    return "web"


class EvidenceRetriever:
    def __init__(self, settings: Settings | None = None, tavily_client: TavilyClient | None = None) -> None:
        self.settings = settings or get_settings()
        if tavily_client is not None:
            self.client = tavily_client
        elif self.settings.tavily_api_key:
            self.client = TavilyClient(api_key=self.settings.tavily_api_key)
        else:
            self.client = None

    async def retrieve_for_claims(self, claims: list[str]) -> list[ClaimEvidence]:
        return [await self.retrieve(claim) for claim in claims]

    async def retrieve(self, claim: str) -> ClaimEvidence:
        if self.client is None:
            raise ExternalServiceError("TAVILY_API_KEY is not configured")

        async def operation() -> ClaimEvidence:
            response = self.client.search(
                query=claim,
                search_depth=self.settings.tavily_search_depth,
                max_results=self.settings.tavily_results_per_claim,
                include_answer=False,
            )
            results = response.get("results", [])
            evidence = [
                EvidenceSource(
                    title=item.get("title"),
                    url=item["url"],
                    content=item.get("content") or item.get("raw_content") or item.get("snippet") or "",
                    score=item.get("score"),
                    reliability=domain_reliability(item["url"]),
                    source_type=source_type(item["url"]),
                )
                for item in results
                if item.get("url") and (item.get("content") or item.get("raw_content") or item.get("snippet"))
            ]
            evidence.sort(key=lambda item: (item.reliability, item.score or 0), reverse=True)
            return ClaimEvidence(claim=claim, evidence=evidence)

        return await with_retries(operation, self.settings, "Tavily search")
