import os

from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app


def test_version():
    client = TestClient(app)
    response = client.get("/version")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "truthgraph"
    assert body["version"]


def test_metrics():
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "http_requests_total" in response.text


def test_error():
    client = TestClient(app)
    response = client.get("/error")
    assert response.status_code == 500


def test_health_fail_ready(monkeypatch):
    monkeypatch.setenv("FAIL_READY", "1")
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 503


def test_health_still_checks_neo4j():
    os.environ.pop("FAIL_READY", None)

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
