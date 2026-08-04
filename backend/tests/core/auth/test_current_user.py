"""
Unit tests for current_user dependencies.
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.auth.current_user import (
    get_current_active_user,
    get_current_superuser,
    get_current_user,
)
from app.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
)
from app.models.user import User
from app.services.auth_service import AuthService


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def auth_service() -> MagicMock:
    """Mock AuthService."""

    return MagicMock(spec=AuthService)


@pytest.fixture
def sample_user() -> User:
    """Return a sample authenticated user."""

    return User(
        id=uuid4(),
        email="admin@example.com",
        password_hash="hashed-password",
        full_name="Administrator",
        is_active=True,
        is_superuser=True,
        email_verified=True,
    )


# =============================================================================
# TestGetCurrentUser
# =============================================================================


class TestGetCurrentUser:
    """Tests for get_current_user()."""

    def test_get_current_user_success(
        self,
        auth_service: MagicMock,
        sample_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Should return authenticated user."""

        auth_service.get_current_user.return_value = sample_user

        monkeypatch.setattr(
            "app.core.auth.current_user.decode_token",
            lambda token: {
                "sub": str(sample_user.id),
            },
        )

        user = get_current_user(
            token="jwt-token",
            auth_service=auth_service,
        )

        assert user == sample_user

        auth_service.get_current_user.assert_called_once_with(
            sample_user.id,
        )

    def test_get_current_user_missing_subject(
        self,
        auth_service: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """JWT without subject should fail."""

        monkeypatch.setattr(
            "app.core.auth.current_user.decode_token",
            lambda token: {},
        )

        with pytest.raises(AuthenticationException):
            get_current_user(
                token="jwt-token",
                auth_service=auth_service,
            )

        auth_service.get_current_user.assert_not_called()

    def test_get_current_user_not_found(
        self,
        auth_service: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Unknown user should fail."""

        user_id = uuid4()

        auth_service.get_current_user.return_value = None

        monkeypatch.setattr(
            "app.core.auth.current_user.decode_token",
            lambda token: {
                "sub": str(user_id),
            },
        )

        with pytest.raises(AuthenticationException):
            get_current_user(
                token="jwt-token",
                auth_service=auth_service,
            )

        auth_service.get_current_user.assert_called_once_with(
            user_id,
        )


# =============================================================================
# TestGetCurrentActiveUser
# =============================================================================


class TestGetCurrentActiveUser:
    """Tests for get_current_active_user()."""

    def test_get_current_active_user_success(
        self,
        sample_user: User,
    ) -> None:
        """Active user should be returned."""

        user = get_current_active_user(sample_user)

        assert user == sample_user

    def test_get_current_active_user_inactive(
        self,
        sample_user: User,
    ) -> None:
        """Inactive users should be rejected."""

        sample_user.is_active = False

        with pytest.raises(AuthorizationException):
            get_current_active_user(sample_user)


# =============================================================================
# TestGetCurrentSuperuser
# =============================================================================


class TestGetCurrentSuperuser:
    """Tests for get_current_superuser()."""

    def test_get_current_superuser_success(
        self,
        sample_user: User,
    ) -> None:
        """Superuser should be returned."""

        user = get_current_superuser(sample_user)

        assert user == sample_user

    def test_get_current_superuser_regular_user(
        self,
        sample_user: User,
    ) -> None:
        """Regular users should be rejected."""

        sample_user.is_superuser = False

        with pytest.raises(AuthorizationException):
            get_current_superuser(sample_user)
