"""
Unit tests for AuthService.authenticate_user().
"""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.core.config import settings
from app.core.exceptions import AuthenticationException
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    LoginResponse,
    TokenData,
)
from app.services.auth_service import AuthService

# --------------------------------------------
#  fixtures
# --------------------------------------------


@pytest.fixture
def repository() -> MagicMock:
    """Mock UserRepository."""

    return MagicMock(spec=UserRepository)


@pytest.fixture
def auth_service(
    repository: MagicMock,
) -> AuthService:
    """Return AuthService."""

    return AuthService(repository)


@pytest.fixture
def sample_user() -> User:
    """Return a sample active user."""

    return User(
        id=uuid4(),
        email="admin@example.com",
        password_hash="hashed-password",
        full_name="Administrator",
        is_active=True,
        is_superuser=True,
        email_verified=True,
        last_login=None,
    )


# -----------------------------------------
# TestAuthenticateUser
# -----------------------------------------


class TestAuthenticateUser:
    """Tests for AuthService.authenticate_user()."""

    def test_authenticate_success(
        self,
        auth_service: AuthService,
        repository: MagicMock,
        sample_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        authenticate_user() should return the user for valid credentials.
        """

        repository.get_by_email.return_value = sample_user

        monkeypatch.setattr(
            "app.services.auth_service.verify_password",
            lambda plain, hashed: True,
        )

        result = auth_service.authenticate_user(
            email="admin@example.com",
            password="password123",
        )

        assert result == sample_user

        repository.get_by_email.assert_called_once_with(
            "admin@example.com",
        )

    def test_unknown_email(
        self,
        auth_service: AuthService,
        repository: MagicMock,
    ) -> None:
        """
        authenticate_user() should raise AuthenticationException
        when the email does not exist.
        """

        repository.get_by_email.return_value = None

        with pytest.raises(AuthenticationException) as exc_info:
            auth_service.authenticate_user(
                email="unknown@example.com",
                password="password123",
            )

        repository.get_by_email.assert_called_once_with(
            "unknown@example.com",
        )

        assert "Invalid" in str(exc_info.value)

    def test_invalid_password(
        self,
        auth_service: AuthService,
        repository: MagicMock,
        sample_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        authenticate_user() should raise AuthenticationException
        when password verification fails.
        """

        repository.get_by_email.return_value = sample_user

        monkeypatch.setattr(
            "app.services.auth_service.verify_password",
            lambda plain, hashed: False,
        )

        with pytest.raises(AuthenticationException) as exc_info:
            auth_service.authenticate_user(
                email="admin@example.com",
                password="wrong-password",
            )

        repository.get_by_email.assert_called_once_with(
            "admin@example.com",
        )

        assert "Invalid" in str(exc_info.value)

    def test_inactive_user(
        self,
        auth_service: AuthService,
        repository: MagicMock,
        sample_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        authenticate_user() should reject inactive users.
        """

        sample_user.is_active = False

        repository.get_by_email.return_value = sample_user

        #
        # Only required if authenticate_user()
        # verifies password before checking is_active.
        #
        monkeypatch.setattr(
            "app.services.auth_service.verify_password",
            lambda plain, hashed: True,
        )

        with pytest.raises(AuthenticationException) as exc_info:
            auth_service.authenticate_user(
                email="admin@example.com",
                password="password123",
            )

        repository.get_by_email.assert_called_once_with(
            "admin@example.com",
        )

        assert "inactive" in str(exc_info.value).lower()


# ----------------------------------------
# TestLogin
# ----------------------------------------


class TestLogin:
    """Tests for AuthService.login()."""

    def test_login_success(
        self,
        auth_service: AuthService,
        repository: MagicMock,
        sample_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        login() should authenticate the user and return LoginResponse.
        """

        repository.get_by_email.return_value = sample_user
        repository.update_last_login.return_value = sample_user

        monkeypatch.setattr(
            "app.services.auth_service.verify_password",
            lambda plain, hashed: True,
        )

        monkeypatch.setattr(
            "app.services.auth_service.create_access_token",
            lambda subject: "access-token",
        )

        monkeypatch.setattr(
            "app.services.auth_service.create_refresh_token",
            lambda subject: "refresh-token",
        )

        response = auth_service.login(
            email="admin@example.com",
            password="password123",
        )

        #
        # Response
        #
        assert isinstance(response, LoginResponse)

        #
        # Tokens
        #
        assert response.tokens.access_token == "access-token"
        assert response.tokens.refresh_token == "refresh-token"
        assert response.tokens.token_type == "bearer"
        assert response.tokens.expires_in == settings.jwt_access_token_expire_minutes * 60

        #
        # User
        #
        assert response.user.id == sample_user.id
        assert response.user.email == sample_user.email
        assert response.user.full_name == sample_user.full_name
        assert response.user.is_active == sample_user.is_active
        assert response.user.is_superuser == sample_user.is_superuser
        assert response.user.email_verified == sample_user.email_verified

        #
        # Repository interactions
        #
        repository.get_by_email.assert_called_once_with(
            "admin@example.com",
        )

        repository.update_last_login.assert_called_once_with(
            sample_user,
        )

    def test_login_updates_last_login(
        self,
        auth_service: AuthService,
        repository: MagicMock,
        sample_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """
        login() should update the user's last login timestamp.
        """

        repository.get_by_email.return_value = sample_user
        repository.update_last_login.return_value = sample_user

        monkeypatch.setattr(
            "app.services.auth_service.verify_password",
            lambda plain, hashed: True,
        )

        monkeypatch.setattr(
            "app.services.auth_service.create_access_token",
            lambda subject: "access-token",
        )

        monkeypatch.setattr(
            "app.services.auth_service.create_refresh_token",
            lambda subject: "refresh-token",
        )

        auth_service.login(
            email="admin@example.com",
            password="password123",
        )

        repository.update_last_login.assert_called_once_with(
            sample_user,
        )


# ----------------------------------------------------------------
# TestRefreshToken
# ----------------------------------------------------------------


class TestRefreshToken:
    """Tests for AuthService.refresh_access_token()."""

    def test_refresh_success(
        self,
        auth_service: AuthService,
        repository: MagicMock,
        sample_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Valid refresh token should return a new access token."""

        repository.get_by_id.return_value = sample_user

        monkeypatch.setattr(
            "app.services.auth_service.decode_token",
            lambda token: {
                "sub": str(sample_user.id),
                "type": "refresh",
            },
        )

        monkeypatch.setattr(
            "app.services.auth_service.is_refresh_token",
            lambda payload: True,
        )

        monkeypatch.setattr(
            "app.services.auth_service.create_access_token",
            lambda subject: "new-access-token",
        )

        response = auth_service.refresh_access_token(
            "refresh-token",
        )

        assert isinstance(response, TokenData)

        assert response.access_token == "new-access-token"
        assert response.refresh_token == "refresh-token"
        assert response.token_type == "bearer"
        assert response.expires_in == settings.jwt_access_token_expire_minutes * 60

        repository.get_by_id.assert_called_once_with(
            sample_user.id,
        )

    def test_refresh_invalid_token(
        self,
        auth_service: AuthService,
        repository: MagicMock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Invalid refresh token should raise AuthenticationException."""

        monkeypatch.setattr(
            "app.services.auth_service.decode_token",
            lambda token: {
                "sub": "12345678-1234-1234-1234-123456789012",
                "type": "access",
            },
        )

        monkeypatch.setattr(
            "app.services.auth_service.is_refresh_token",
            lambda payload: False,
        )

        with pytest.raises(AuthenticationException):
            auth_service.refresh_access_token(
                "invalid-token",
            )

        repository.get_by_id.assert_not_called()

    def test_refresh_user_not_found(
        self,
        auth_service: AuthService,
        repository: MagicMock,
        sample_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Unknown user should raise AuthenticationException."""

        repository.get_by_id.return_value = None

        monkeypatch.setattr(
            "app.services.auth_service.decode_token",
            lambda token: {
                "sub": str(sample_user.id),
                "type": "refresh",
            },
        )

        monkeypatch.setattr(
            "app.services.auth_service.is_refresh_token",
            lambda payload: True,
        )

        with pytest.raises(AuthenticationException):
            auth_service.refresh_access_token(
                "refresh-token",
            )

        repository.get_by_id.assert_called_once_with(
            sample_user.id,
        )

    def test_refresh_inactive_user(
        self,
        auth_service: AuthService,
        repository: MagicMock,
        sample_user: User,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Inactive users should not receive new access tokens."""

        sample_user.is_active = False

        repository.get_by_id.return_value = sample_user

        monkeypatch.setattr(
            "app.services.auth_service.decode_token",
            lambda token: {
                "sub": str(sample_user.id),
                "type": "refresh",
            },
        )

        monkeypatch.setattr(
            "app.services.auth_service.is_refresh_token",
            lambda payload: True,
        )

        with pytest.raises(AuthenticationException):
            auth_service.refresh_access_token(
                "refresh-token",
            )

        repository.get_by_id.assert_called_once_with(
            sample_user.id,
        )


# ----------------------------------------------------------------
# TestUserOperations
# ----------------------------------------------------------------


class TestUserOperations:
    """Tests for AuthService user helper methods."""

    def test_get_current_user(
        self,
        auth_service: AuthService,
        repository: MagicMock,
        sample_user: User,
    ) -> None:
        """Should return the user from the repository."""

        repository.get_by_id.return_value = sample_user

        result = auth_service.get_current_user(
            sample_user.id,
        )

        assert result == sample_user

        repository.get_by_id.assert_called_once_with(
            sample_user.id,
        )

    def test_get_current_user_not_found(
        self,
        auth_service: AuthService,
        repository: MagicMock,
    ) -> None:
        """Unknown user should return None."""

        repository.get_by_id.return_value = None

        result = auth_service.get_current_user(
            uuid4(),
        )

        assert result is None

        repository.get_by_id.assert_called_once()

    def test_update_last_login(
        self,
        auth_service: AuthService,
        repository: MagicMock,
        sample_user: User,
    ) -> None:
        """Should delegate last-login update to the repository."""

        auth_service.update_last_login(sample_user)

        repository.update_last_login.assert_called_once_with(
            sample_user,
        )
