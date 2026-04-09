"""
tests/api/test_health.py — Tests for GET /health endpoint.
"""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app, raise_server_exceptions=True)


class TestHealthEndpoint:
    def test_returns_200(self) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_status_is_ok(self) -> None:
        response = client.get("/health")
        assert response.json()["status"] == "ok"

    def test_environment_field_present(self) -> None:
        response = client.get("/health")
        assert "environment" in response.json()

    def test_environment_defaults_to_commercial(self) -> None:
        response = client.get("/health")
        assert response.json()["environment"] == "commercial"

    def test_index_document_count_present(self) -> None:
        response = client.get("/health")
        assert "index_document_count" in response.json()

    def test_content_type_is_json(self) -> None:
        response = client.get("/health")
        assert "application/json" in response.headers["content-type"]
