from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app
from app.models import ClaimVerdict, VerificationResponse


def test_health():
    class MockRepository:
        def __init__(self, settings):
            pass

        def verify_connection(self):
            return None

    with patch("app.main.Neo4jGraphRepository", MockRepository):
        client = TestClient(app)

        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "neo4j": "connected"}


def test_verify_endpoint(monkeypatch):
    class MockPipeline:
        async def verify(self, raw_input, input_type):
            return VerificationResponse(
                overall_verdict="true",
                overall_confidence=95,
                credibility_score=100,
                claims=[
                    ClaimVerdict(
                        claim="Apollo 11 landed on the Moon in 1969.",
                        verdict="true",
                        confidence=95,
                        reasoning="NASA evidence supports the claim.",
                        supporting_sources=["https://www.nasa.gov/apollo-11"],
                    )
                ],
            )

    monkeypatch.setattr("app.main.get_pipeline", lambda: MockPipeline())
    client = TestClient(app)

    response = client.post("/verify", json={"input": "Apollo 11 landed on the Moon in 1969.", "type": "text"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["overall_verdict"] == "true"
    assert payload["claims"][0]["confidence"] == 95
