"""
Authentication service.

Business logic for user authentication.
"""

from __future__ import annotations

from uuid import UUID

from app.core.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_token,
    is_refresh_token,
)
from app.core.security.password import verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    TokenData,
    AuthenticatedUser,
    LoginResponse,
)
from app.core.config import settings
from app.core.exceptions import AuthenticationException


class AuthService:
    """
    Authentication service.
    """

    def __init__(
        self,
        repository: UserRepository,
    ) -> None:
        self._repository = repository

    # -------------------------------------------------------------------------
    # Authentication
    # -------------------------------------------------------------------------

    def authenticate_user(
        self,
        email: str,
        password: str,
    ) -> User :
        """
        Authenticate a user using email and password.
        """

        user = self._repository.get_by_email(email)

        if user is None:
            raise AuthenticationException("Invalid email or password")
        
        if not user.is_active:
            raise AuthenticationException("User account is inactive")

        if not verify_password(password, user.password_hash):
            raise AuthenticationException("Invalid email or password")

        return user

    # -------------------------------------------------------------------------
    # Login
    # -------------------------------------------------------------------------

    def login(
        self,
        email: str,
        password: str,
    ) -> LoginResponse :
        """
        Authenticate a user and issue JWT tokens.
        """

        user = self.authenticate_user(email, password)

        self._repository.update_last_login(user)

        return LoginResponse(
            tokens=TokenData(
                access_token=create_access_token( subject=str(user.id),),
                refresh_token=create_refresh_token( subject=str(user.id),),
                token_type="bearer",
                expires_in=settings.jwt_access_token_expire_minutes * 60 ,
            ),
            user=AuthenticatedUser.model_validate(user),
        )

    # -------------------------------------------------------------------------
    # Refresh Token
    # -------------------------------------------------------------------------

    def refresh_access_token(
        self,
        refresh_token: str,
    ) -> TokenData:
        """
        Issue a new access token from a refresh token.
        """

        payload = decode_token(refresh_token)

        if not is_refresh_token(payload):
            raise AuthenticationException( "Invalid refresh token",)

        user = self._repository.get_by_id(
            UUID(payload["sub"]),
        )

        if user is None:
            raise AuthenticationException( "User not found",)

        if not user.is_active:
            raise AuthenticationException( "User account is inactive",)

        return TokenData(
            access_token=create_access_token(
                subject=str(user.id),
            ),
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        )

    # -------------------------------------------------------------------------
    # User
    # -------------------------------------------------------------------------

    def get_current_user(
        self,
        user_id: UUID,
    ) -> User | None:
        """Return the user or None if the ID does not exist."""
        return self._repository.get_by_id(user_id)

    def update_last_login(
        self,
        user: User,
    ) -> None:
        """
        Update the user's last login timestamp.
        """

        self._repository.update_last_login(user)
