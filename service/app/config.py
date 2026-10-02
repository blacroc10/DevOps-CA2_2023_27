from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")
    groq_api_key: str | None = Field(default=None, alias="GROQ_API_KEY")

    llama_provider: Literal["groq"] = "groq"
    llama_model: str = "llama-3.1-8b-instant"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    request_timeout_seconds: float = 20.0
    external_retry_count: int = 2
    retry_backoff_seconds: float = 0.5

    tavily_search_depth: Literal["basic", "advanced"] = "advanced"
    tavily_results_per_claim: int = 5
    max_claims: int = 5
    graph_confidence_k: float = 2.5
    direct_evidence_hop_distance: int = 1
    relationship_similarity_threshold: float = 0.18
    neo4j_enabled: bool = True
    neo4j_uri: str | None = Field(default=None, alias="NEO4J_URI")
    neo4j_user: str | None = Field(default=None, alias="NEO4J_USER")
    neo4j_password: str | None = Field(default=None, alias="NEO4J_PASSWORD")
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000,http://localhost:4173,http://127.0.0.1:4173",
        alias="CORS_ORIGINS",
    )

    def allowed_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
