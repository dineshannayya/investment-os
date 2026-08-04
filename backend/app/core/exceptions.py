"""
Application exception hierarchy.

Defines the canonical exception types used throughout Investment OS.
"""

from __future__ import annotations

from app.core.config.error_codes import ErrorCode

from http import HTTPStatus

from typing import Any

class AppException(Exception):
    """
    Base class for all application exceptions.
    """

    def __init__(
        self,
        *,
        code: ErrorCode,
        message: str,
        status_code: int,
        field: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)

        self.code = code
        self.message = message
        self.status_code = status_code
        self.field = field
        self.details = details or {}

class ValidationException(AppException):
    """Raised when request validation fails."""

    def __init__(
        self,
        message: str,
        *,
        field: str | None = None,
        details: dict | None = None,
    ) -> None:
        super().__init__(
            code=ErrorCode.VALIDATION_ERROR,
            message=message,
            status_code=HTTPStatus.BAD_REQUEST,
            field=field,
            details=details,
        )


class AuthenticationException(AppException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed.") -> None:
        super().__init__(
            code=ErrorCode.AUTHENTICATION_FAILED,
            message=message,
            status_code=HTTPStatus.UNAUTHORIZED,
        )


class AuthorizationException(AppException):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Access denied.") -> None:
        super().__init__(
            code=ErrorCode.ACCESS_DENIED,
            message=message,
            status_code=HTTPStatus.FORBIDDEN,
        )


class NotFoundException(AppException):
    """Raised when a resource cannot be found."""

    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(
            code=ErrorCode.RESOURCE_NOT_FOUND,
            message=message,
            status_code=HTTPStatus.NOT_FOUND,
        )


class ConflictException(AppException):
    """Raised when a resource conflict occurs."""

    def __init__(self, message: str = "Resource conflict.") -> None:
        super().__init__(
            code=ErrorCode.RESOURCE_CONFLICT,
            message=message,
            status_code=HTTPStatus.CONFLICT,
        )


class BusinessRuleException(AppException):
    """Raised when a business rule is violated."""

    def __init__(self, message: str) -> None:
        super().__init__(
            code=ErrorCode.BUSINESS_RULE_VIOLATION,
            message=message,
            status_code=HTTPStatus.UNPROCESSABLE_ENTITY,
        )


class DatabaseException(AppException):
    """Raised for database-related failures."""

    def __init__(self, message: str = "Database operation failed.") -> None:
        super().__init__(
            code=ErrorCode.DATABASE_ERROR,
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )


class ExternalServiceException(AppException):
    """Raised when an external service call fails."""

    def __init__(self, message: str = "External service unavailable.") -> None:
        super().__init__(
            code=ErrorCode.EXTERNAL_SERVICE_ERROR,
            message=message,
            status_code=HTTPStatus.SERVICE_UNAVAILABLE,
        )


class InternalServerException(AppException):
    """Raised for unexpected internal failures."""

    def __init__(self, message: str = "Internal server error.") -> None:
        super().__init__(
            code=ErrorCode.INTERNAL_ERROR,
            message=message,
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
        )
