"""
OAuth2 configuration.

Defines the OAuth2 Bearer authentication scheme used by FastAPI.
"""

from __future__ import annotations

from fastapi.security import OAuth2PasswordBearer

from app.core.config import API_PREFIX


# =============================================================================
# OAuth2 Bearer Scheme
# =============================================================================

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{API_PREFIX}/auth/login",
    scheme_name="JWT",
    description="JWT Bearer authentication",
    auto_error=True,
)


# =============================================================================
# Public Exports
# =============================================================================

__all__ = [
    "oauth2_scheme",
]
