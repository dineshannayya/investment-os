"""
Unit tests for authentication dependency providers.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from sqlalchemy.orm import Session

from app.core.auth.dependencies import (
    get_auth_service,
    get_user_repository,
)
from app.repositories.user_repository import UserRepository
from app.services.auth_service import AuthService


# =============================================================================
# TestGetUserRepository
# =============================================================================


class TestGetUserRepository:
    """Tests for get_user_repository()."""

    def test_returns_user_repository(self) -> None:
        """Should create a UserRepository using the supplied session."""

        db = MagicMock(spec=Session)

        repository = get_user_repository(db)

        assert isinstance(repository, UserRepository)
        assert repository._session is db


# =============================================================================
# TestGetAuthService
# =============================================================================


class TestGetAuthService:
    """Tests for get_auth_service()."""

    def test_returns_auth_service(self) -> None:
        """Should create an AuthService using the supplied repository."""

        repository = MagicMock(spec=UserRepository)

        service = get_auth_service(repository)

        assert isinstance(service, AuthService)
        assert service._repository is repository
