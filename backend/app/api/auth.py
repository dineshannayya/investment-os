"""
Authentication API.

Authentication endpoints.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from app.core.config import settings

from app.core.auth import (
    get_auth_service,
    get_current_active_user,
)
from app.models.user import User
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshTokenRequest,
    RefreshTokenResponse,
    AuthenticatedUser,
)
from app.schemas.response import ApiResponse
from app.services.auth_service import AuthService

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# =============================================================================
# Login
# =============================================================================


@router.post(
    "/login",
    response_model=ApiResponse[LoginResponse],
    status_code=status.HTTP_200_OK,
    summary="User Login",
)
def login(
    request: LoginRequest,
    auth_service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> ApiResponse[LoginResponse]:
    """
    Authenticate a user and return JWT tokens.
    """

    result = auth_service.login(
        email=request.email,
        password=request.password,
    )

    return ApiResponse.ok(
        data=result,
        message="Login successful",
    )


# =============================================================================
# Refresh Token
# =============================================================================


@router.post(
    "/refresh",
    response_model=ApiResponse[RefreshTokenResponse],
    status_code=status.HTTP_200_OK,
    summary="Refresh Access Token",
)
def refresh_token(
    request: RefreshTokenRequest,
    auth_service: Annotated[
        AuthService,
        Depends(get_auth_service),
    ],
) -> ApiResponse[RefreshTokenResponse]:
    """
    Issue a new access token.
    """

    access_token = auth_service.refresh_access_token(
        request.refresh_token,
    )

    return ApiResponse.ok(
        data=RefreshTokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.jwt_access_token_expire_minutes * 60,
        ),
        message="Token refreshed",
    )


# =============================================================================
# Current User
# =============================================================================


@router.get(
    "/me",
    response_model=ApiResponse[AuthenticatedUser],
    status_code=status.HTTP_200_OK,
    summary="Current User",
)
def get_current_user(
    current_user: Annotated[
        User,
        Depends(get_current_active_user),
    ],
) -> ApiResponse[AuthenticatedUser]:
    """
    Return the currently authenticated user.
    """

    return ApiResponse.ok(
        data=AuthenticatedUser.model_validate(
            current_user,
            from_attributes=True,
        ),
        message="Current user retrieved",
    )
