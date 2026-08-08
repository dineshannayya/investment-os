"""
Authentication dependencies.

FastAPI dependency providers for authentication services.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database.dependencies import get_db
from app.repositories.user import UserRepository
from app.services.auth_service import AuthService

# =============================================================================
# Repository Dependencies
# =============================================================================


def get_user_repository(
    db: Annotated[Session, Depends(get_db)],
) -> UserRepository:
    """
    Return a UserRepository instance.
    """

    return UserRepository(db)


# =============================================================================
# Service Dependencies
# =============================================================================


def get_auth_service(
    repository: Annotated[
        UserRepository,
        Depends(get_user_repository),
    ],
) -> AuthService:
    """
    Return an AuthService instance.
    """

    return AuthService(repository)


# =============================================================================
# Public Exports
# =============================================================================


__all__ = [
    "get_user_repository",
    "get_auth_service",
]
