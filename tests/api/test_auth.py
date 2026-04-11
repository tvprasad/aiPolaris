"""
tests/api/test_auth.py — Tests for auth middleware reachable without a live Entra ID.

auth_enabled=False (set in local .env) enables the dev bypass path.
Tests here exercise that path and the lifespan startup/shutdown.
"""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from api.main import app
from api.middleware.auth import _validate_jwt, validate_token


class TestValidateTokenDevBypass:
    """
    auth_enabled=False is set in .env for local dev — these tests
    exercise the dev bypass branch of validate_token.
    """

    async def test_dev_bypass_returns_admin_claims(self) -> None:
        mock_request = MagicMock()
        result = await validate_token(mock_request)
        # dev bypass always returns local-dev admin claims
        assert result["oid"] == "local-dev"
        assert "admin" in result["roles"]
        assert result["name"] == "Local Developer"


class TestValidateJwt:
    def test_stub_returns_dict(self) -> None:
        from api.config import get_settings

        settings = get_settings()
        result = _validate_jwt("any-token", settings)
        assert result is not None
        assert "oid" in result
        assert "roles" in result


class TestLifespan:
    def test_lifespan_startup_and_shutdown(self) -> None:
        """Using TestClient as context manager triggers lifespan startup + shutdown."""
        with TestClient(app, raise_server_exceptions=True) as client:
            response = client.get("/health")
            assert response.status_code == 200
