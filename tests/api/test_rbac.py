"""
tests/api/test_rbac.py — Unit tests for RBAC helpers and capability enforcement.

Tests _get_capabilities and _roles_with_capability directly (pure functions),
plus the require_capability dependency via FastAPI dependency_overrides.
"""

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.middleware.auth import validate_token
from api.middleware.rbac import (
    ROLE_CAPABILITIES,
    _get_capabilities,
    _roles_with_capability,
)


# ── Pure function tests ───────────────────────────────────────────────────────

class TestGetCapabilities:
    def test_user_role_grants_query(self) -> None:
        caps = _get_capabilities(["user"])
        assert "query" in caps

    def test_operator_role_grants_ingest(self) -> None:
        caps = _get_capabilities(["operator"])
        assert "ingest" in caps
        assert "query" in caps
        assert "settings" in caps

    def test_admin_role_grants_all(self) -> None:
        caps = _get_capabilities(["admin"])
        assert "query" in caps
        assert "ingest" in caps
        assert "eval" in caps
        assert "audit" in caps

    def test_empty_roles_returns_empty_set(self) -> None:
        caps = _get_capabilities([])
        assert caps == set()

    def test_unknown_role_returns_empty_set(self) -> None:
        caps = _get_capabilities(["nonexistent-role"])
        assert caps == set()

    def test_multiple_roles_union(self) -> None:
        caps = _get_capabilities(["user", "operator"])
        assert "query" in caps
        assert "ingest" in caps


class TestRolesWithCapability:
    def test_query_is_available_to_user_role(self) -> None:
        roles = _roles_with_capability("query")
        assert "user" in roles

    def test_ingest_not_available_to_user(self) -> None:
        roles = _roles_with_capability("ingest")
        assert "user" not in roles
        assert "operator" in roles

    def test_unknown_capability_returns_empty(self) -> None:
        roles = _roles_with_capability("nonexistent")
        assert roles == []

    def test_eval_only_for_admin(self) -> None:
        roles = _roles_with_capability("eval")
        assert roles == ["admin"]


# ── Dependency override tests (require_capability) ───────────────────────────

def _make_operator_claims() -> dict:
    return {"roles": ["operator"], "oid": "user-oid-123", "name": "Test Operator"}


def _make_user_claims() -> dict:
    return {"roles": ["user"], "oid": "user-oid-456", "name": "Test User"}


class TestRequireCapabilityViaIngest:
    """Test require_capability through the /ingest endpoint."""

    def test_operator_can_call_ingest(self) -> None:
        app.dependency_overrides[validate_token] = _make_operator_claims
        try:
            client = TestClient(app, raise_server_exceptions=True)
            response = client.post(
                "/ingest",
                json={"site_id": "site-1", "drive_id": "drive-1"},
            )
            assert response.status_code == 200
        finally:
            app.dependency_overrides.pop(validate_token, None)

    def test_user_role_blocked_from_ingest(self) -> None:
        app.dependency_overrides[validate_token] = _make_user_claims
        try:
            client = TestClient(app, raise_server_exceptions=False)
            response = client.post(
                "/ingest",
                json={"site_id": "site-1", "drive_id": "drive-1"},
            )
            assert response.status_code == 403
        finally:
            app.dependency_overrides.pop(validate_token, None)

    def test_ingest_response_has_pull_id(self) -> None:
        app.dependency_overrides[validate_token] = _make_operator_claims
        try:
            client = TestClient(app, raise_server_exceptions=True)
            response = client.post(
                "/ingest",
                json={"site_id": "site-1", "drive_id": "drive-1"},
            )
            assert "pull_id" in response.json()
        finally:
            app.dependency_overrides.pop(validate_token, None)
