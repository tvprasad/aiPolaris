"""
api/middleware/rbac.py — Role-based capability scope check.

Maps Entra ID roles to allowed capabilities.
RBAC checks happen here in middleware — NEVER in route handlers.
Satisfies NIST AC-2 (Account Management) and AC-5 (Separation of Duties).

SECURITY NOTE: Run challenge mode after any change.
"Challenge the RBAC middleware. 3 bypass paths: token replay,
 role escalation, missing scope check on /ingest."
"""

from typing import Any, cast

from fastapi import Depends, HTTPException, Request, status

from api.middleware.auth import validate_token

# Role → capability mapping
# Add new roles here — never inline in route handlers
ROLE_CAPABILITIES: dict[str, list[str]] = {
    "user": ["query"],
    "operator": ["query", "ingest", "settings"],
    "admin": ["query", "ingest", "settings", "eval", "audit"],
}


def require_capability(capability: str) -> Any:
    """
    FastAPI dependency factory.
    Usage: Depends(require_capability("ingest"))
    """

    async def _check(
        request: Request,
        claims: dict[str, object] = Depends(validate_token),
    ) -> dict[str, object]:
        roles: list[str] = cast(list[str], claims.get("roles", []))
        allowed = _get_capabilities(roles)

        if capability not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Capability '{capability}' requires one of: "
                    f"{_roles_with_capability(capability)}. "
                    f"Token has roles: {roles}"
                ),
            )

        # Attach claims to request state for route handlers
        request.state.user_oid = claims.get("oid")
        request.state.user_name = claims.get("name")
        request.state.roles = roles
        return claims

    return _check


def _get_capabilities(roles: list[str]) -> set[str]:
    """Union of capabilities across all roles the user holds."""
    capabilities: set[str] = set()
    for role in roles:
        capabilities.update(ROLE_CAPABILITIES.get(role, []))
    return capabilities


def _roles_with_capability(capability: str) -> list[str]:
    """Which roles grant a given capability — used in error messages."""
    return [role for role, caps in ROLE_CAPABILITIES.items() if capability in caps]
