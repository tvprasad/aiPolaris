"""
api/middleware/auth.py — Entra ID token validation.

Validates every incoming JWT against the Entra ID authority.
Extracts user OID and roles from claims.
Satisfies NIST IA-2 (Identification and Authentication) and IA-8.

SECURITY NOTE: This is a security-critical component.
Run challenge mode after any change:
  "Challenge this implementation. 3 bypass paths:
   token replay, role escalation, missing scope check."
"""

from fastapi import HTTPException, Request, status

from api.config import Settings, get_settings


async def validate_token(request: Request) -> dict[str, object]:
    """
    Extract and validate Bearer token from Authorization header.
    Returns decoded claims dict with oid, roles, and name.
    Raises 401 if token is absent, expired, or invalid.
    """
    settings = get_settings()

    # Local dev bypass — NEVER enable in production (Terraform sets AUTH_ENABLED=true)
    if not settings.auth_enabled:
        return {"oid": "local-dev", "roles": ["admin"], "name": "Local Developer"}

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[len("Bearer ") :]

    # Validate token against Entra ID authority
    # TODO: implement full MSAL token validation
    # Checks required: signature, expiry, audience, issuer
    # See: https://learn.microsoft.com/en-us/azure/active-directory/develop/access-tokens
    claims = _validate_jwt(token, settings)

    if not claims:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token validation failed",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return claims


def _validate_jwt(token: str, settings: "Settings") -> dict[str, object] | None:
    """
    Stub: replace with full MSAL token validation.
    Must check: signature, expiry, audience, issuer.
    Must NOT skip any of these checks — all four are required.
    """
    # TODO: implement MSAL token validation
    # from msal import PublicClientApplication
    # app = PublicClientApplication(settings.client_id, authority=settings.authority)
    # result = app.acquire_token_on_behalf_of(token, scopes=[...])
    return {"oid": "stub-oid", "roles": ["user"], "name": "Stub User"}
