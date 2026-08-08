"""
Unit tests for application exceptions.
"""

from __future__ import annotations

from http import HTTPStatus

from app.core.config.error_codes import ErrorCode
from app.core.exceptions import (
    AppException,
    AuthenticationException,
    AuthorizationException,
    BusinessRuleException,
    ConflictException,
    DatabaseException,
    ExternalServiceException,
    InternalServerException,
    NotFoundException,
    ValidationException,
)

# -------------------------------------------
# Base Exception
# -------------------------------------------


class TestAppException:
    """Tests for AppException."""

    def test_app_exception(self) -> None:
        exc = AppException(
            code=ErrorCode.INTERNAL_ERROR,
            message="Boom",
            status_code=500,
            field="email",
            details={"id": 1},
        )

        assert str(exc) == "Boom"
        assert exc.code == ErrorCode.INTERNAL_ERROR
        assert exc.message == "Boom"
        assert exc.status_code == 500
        assert exc.field == "email"
        assert exc.details == {"id": 1}


# -------------------------------------------
# ValidationException
# -------------------------------------------


class TestValidationException:

    def test_validation_exception(self) -> None:
        exc = ValidationException(
            "Invalid email",
            field="email",
        )

        assert isinstance(exc, AppException)
        assert exc.code == ErrorCode.VALIDATION_ERROR
        assert exc.status_code == HTTPStatus.BAD_REQUEST
        assert exc.field == "email"
        assert exc.message == "Invalid email"


# -------------------------------------------
# AuthenticationException
# -------------------------------------------


class TestAuthenticationException:

    def test_default_message(self) -> None:
        exc = AuthenticationException()

        assert exc.code == ErrorCode.AUTHENTICATION_FAILED
        assert exc.status_code == HTTPStatus.UNAUTHORIZED
        assert exc.message == "Authentication failed."

    def test_custom_message(self) -> None:
        exc = AuthenticationException("Invalid password")

        assert exc.message == "Invalid password"


# -------------------------------------------
# AuthorizationException
# -------------------------------------------


class TestAuthorizationException:

    def test_default_message(self) -> None:
        exc = AuthorizationException()

        assert exc.code == ErrorCode.ACCESS_DENIED
        assert exc.status_code == HTTPStatus.FORBIDDEN

    def test_custom_message(self) -> None:
        exc = AuthorizationException("Admin only")

        assert exc.message == "Admin only"


# -------------------------------------------
# NotFoundException
# -------------------------------------------


class TestNotFoundException:

    def test_default_message(self) -> None:
        exc = NotFoundException()

        assert exc.code == ErrorCode.RESOURCE_NOT_FOUND
        assert exc.status_code == HTTPStatus.NOT_FOUND

    def test_custom_message(self) -> None:
        exc = NotFoundException("Startup not found")

        assert exc.message == "Startup not found"


# -------------------------------------------
# ConflictException
# -------------------------------------------


class TestConflictException:

    def test_default_message(self) -> None:
        exc = ConflictException()

        assert exc.code == ErrorCode.RESOURCE_CONFLICT
        assert exc.status_code == HTTPStatus.CONFLICT

    def test_custom_message(self) -> None:
        exc = ConflictException("Duplicate email")

        assert exc.message == "Duplicate email"


# -------------------------------------------
# BusinessRuleException
# -------------------------------------------


class TestBusinessRuleException:

    def test_business_rule_exception(self) -> None:
        exc = BusinessRuleException(
            "Investment limit exceeded",
        )

        assert exc.code == ErrorCode.BUSINESS_RULE_VIOLATION
        assert exc.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
        assert exc.message == "Investment limit exceeded"


# -------------------------------------------
# DatabaseException
# -------------------------------------------


class TestDatabaseException:

    def test_default_message(self) -> None:
        exc = DatabaseException()

        assert exc.code == ErrorCode.DATABASE_ERROR
        assert exc.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

    def test_custom_message(self) -> None:
        exc = DatabaseException("Connection lost")

        assert exc.message == "Connection lost"


# -------------------------------------------
# ExternalServiceException
# -------------------------------------------


class TestExternalServiceException:

    def test_default_message(self) -> None:
        exc = ExternalServiceException()

        assert exc.code == ErrorCode.EXTERNAL_SERVICE_ERROR
        assert exc.status_code == HTTPStatus.SERVICE_UNAVAILABLE

    def test_custom_message(self) -> None:
        exc = ExternalServiceException("OpenAI unavailable")

        assert exc.message == "OpenAI unavailable"


# -------------------------------------------
# InternalServerException
# -------------------------------------------


class TestInternalServerException:

    def test_default_message(self) -> None:
        exc = InternalServerException()

        assert exc.code == ErrorCode.INTERNAL_ERROR
        assert exc.status_code == HTTPStatus.INTERNAL_SERVER_ERROR

    def test_custom_message(self) -> None:
        exc = InternalServerException("Unexpected error")

        assert exc.message == "Unexpected error"
