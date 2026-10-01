"""Phase 1 — Authentication module.

Supabase Auth issues JWTs; this module validates them against the
Supabase project (via the /auth/v1/user endpoint) and exposes a
FastAPI dependency that yields the authenticated user id.

Frontend flow:
  React -> supabase.auth.signIn -> JWT in Authorization: Bearer <token>
  FastAPI -> get_current_user -> user_id
"""

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.database.client import get_supabase_anon, supabase_enabled

bearer_scheme = HTTPBearer(auto_error=False)


class AuthUser:
    """Minimal authenticated identity attached to a request."""

    def __init__(self, user_id: str, email: Optional[str] = None):
        self.id = user_id
        self.email = email

    def __repr__(self) -> str:  # pragma: no cover
        return f"AuthUser(id={self.id!r}, email={self.email!r})"


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> AuthUser:
    """FastAPI dependency: validate the Supabase JWT and return the user.

    Raises 401 when the token is missing/invalid, 503 when Supabase is
    not configured (so misconfiguration is obvious instead of silently
    disabling auth).
    """
    if not supabase_enabled():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured (SUPABASE_URL / SUPABASE_ANON_KEY missing).",
        )
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    try:
        client = get_supabase_anon()
        # Validates the JWT with the Supabase project; raises on invalid/expired.
        res = client.auth.get_user(token)
        user = res.user
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return AuthUser(user_id=str(user.id), email=getattr(user, "email", None))
    except HTTPException:
        raise
    except Exception as exc:  # network/SDK errors → 401 rather than 500
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_optional_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Optional[AuthUser]:
    """Dependency for endpoints that work both anonymously and authed."""
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
