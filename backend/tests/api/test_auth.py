"""
Tests for Authentication API.
"""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.auth.current_user import get_current_active_user
from app.core.auth.dependencies import get_auth_service
from app.core.exceptions import (
    AuthenticationException,
    AuthorizationException,
)
from app.main import app
from app.schemas.auth import (
    AuthenticatedUser,
    LoginResponse,
    TokenData,
)

# Test Class


class TestLogin:
    """Tests for POST /auth/login."""


@pytest.fixture
def authenticated_client(
    authenticated_user: AuthenticatedUser,
):
    app.dependency_overrides[get_current_active_user] = lambda: authenticated_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


@pytest.fixture
def client(mock_auth_service):
    """Test client with overridden AuthService."""

    app.dependency_overrides[get_auth_service] = lambda: mock_auth_service

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# Test 1 — Successful Login


def test_login_success(
    client: TestClient,
    mock_auth_service: MagicMock,
    authenticated_user: AuthenticatedUser,
):
    """Successful login returns JWT tokens."""

    mock_auth_service.login.return_value = LoginResponse(
        tokens=TokenData(
            access_token="access-token",
            refresh_token="refresh-token",
            token_type="bearer",
            expires_in=1800,
        ),
        user=authenticated_user,
    )

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["success"] is True

    assert body["data"]["tokens"]["access_token"] == "access-token"

    assert body["data"]["tokens"]["refresh_token"] == "refresh-token"

    mock_auth_service.login.assert_called_once()


# Test 2 — Invalid Password


def test_invalid_password(
    client: TestClient,
    mock_auth_service: MagicMock,
):
    """Invalid password returns 401."""

    mock_auth_service.login.side_effect = AuthenticationException("Invalid email or password")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "admin@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401


# Test 3 — Unknown Email


def test_unknown_email(
    client: TestClient,
    mock_auth_service: MagicMock,
):
    """Unknown email returns 401."""

    mock_auth_service.login.side_effect = AuthenticationException("Invalid email or password")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "unknown@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 401


# Test 4 — Inactive User


def test_inactive_user(
    client: TestClient,
    mock_auth_service: MagicMock,
):
    """Inactive users cannot log in."""

    mock_auth_service.login.side_effect = AuthorizationException("User account is inactive")

    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "inactive@example.com",
            "password": "Password123!",
        },
    )

    assert response.status_code == 403


# Test 5 — Validation Error


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"email": "admin@example.com"},
        {"password": "Password123!"},
        {
            "email": "invalid-email",
            "password": "Password123!",
        },
    ],
)
def test_login_validation_error(
    client: TestClient,
    payload,
):
    """Invalid request payload returns validation error."""

    response = client.post(
        "/api/v1/auth/login",
        json=payload,
    )

    assert response.status_code == 422


# -------------------------------------
# TestRefreshToken
# -------------------------------------
class TestRefreshToken:
    """Tests for POST /auth/refresh."""

    def test_refresh_success(
        self,
        client: TestClient,
        mock_auth_service: MagicMock,
    ) -> None:
        """Valid refresh token returns a new access token."""

        # mock_auth_service.refresh_access_token.return_value = TokenData(
        #    access_token="new-access-token",
        #    refresh_token="refresh-token",
        #    token_type="bearer",
        #    expires_in=1800,
        # )
        mock_auth_service.refresh_access_token.return_value = "new-access-token"

        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "refresh-token",
            },
        )

        assert response.status_code == 200

        body = response.json()

        assert body["success"] is True
        assert body["data"]["access_token"] == "new-access-token"
        assert body["data"]["token_type"] == "bearer"

        mock_auth_service.refresh_access_token.assert_called_once_with(
            "refresh-token",
        )

    def test_refresh_invalid_token(
        self,
        client: TestClient,
        mock_auth_service: MagicMock,
    ) -> None:
        """Invalid refresh token returns 401."""

        mock_auth_service.refresh_access_token.side_effect = AuthenticationException(
            "Invalid refresh token"
        )

        response = client.post(
            "/api/v1/auth/refresh",
            json={
                "refresh_token": "invalid-token",
            },
        )

        assert response.status_code == 401

    def test_refresh_validation_error(
        self,
        client: TestClient,
    ) -> None:
        """Missing refresh token returns validation error."""

        response = client.post(
            "/api/v1/auth/refresh",
            json={},
        )

        assert response.status_code == 422


# ---------------------------------------
#
# ---------------------------------------
class TestCurrentUser:
    """Tests for GET /auth/me."""

    def test_current_user_success(
        self,
        authenticated_client: TestClient,
        authenticated_user: AuthenticatedUser,
    ) -> None:

        response = authenticated_client.get(
            "/api/v1/auth/me",
        )

        assert response.status_code == 200

        body = response.json()

        assert body["success"] is True
        assert body["data"]["email"] == authenticated_user.email
        assert body["data"]["full_name"] == authenticated_user.full_name

    def test_current_user_unauthenticated(
        self,
        client: TestClient,
    ) -> None:
        """Without dependency override authentication should fail."""

        response = client.get(
            "/api/v1/auth/me",
        )

        assert response.status_code in (401, 403)

    def test_current_user_model(
        self,
        authenticated_client: TestClient,
    ) -> None:

        response = authenticated_client.get(
            "/api/v1/auth/me",
        )

        body = response.json()

        assert body["data"]["is_active"] is True
        assert body["data"]["is_superuser"] is True
