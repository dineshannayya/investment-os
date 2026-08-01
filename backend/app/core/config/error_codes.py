"""
Application error codes.

This module defines the canonical machine-readable error codes used
throughout Investment OS.

These values are part of the public API contract and must remain
stable once released.
"""

from enum import StrEnum


class ErrorCode(StrEnum):
    """Canonical application error codes."""

    # ------------------------------------------------------------------
    # Validation Errors
    # ------------------------------------------------------------------
    INVALID_FORMAT = "invalid_format"
    INVALID_PARAMETER = "invalid_parameter"
    INVALID_REQUEST = "invalid_request"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    VALIDATION_ERROR = "validation_error"

    # ------------------------------------------------------------------
    # Authentication Errors
    # ------------------------------------------------------------------
    AUTHENTICATION_FAILED = "authentication_failed"
    AUTHENTICATION_REQUIRED = "authentication_required"
    INVALID_CREDENTIALS = "invalid_credentials"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_INVALID = "token_invalid"

    # ------------------------------------------------------------------
    # Authorization Errors
    # ------------------------------------------------------------------
    ACCESS_DENIED = "access_denied"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"

    # ------------------------------------------------------------------
    # Resource Errors
    # ------------------------------------------------------------------
    RESOURCE_ALREADY_EXISTS = "resource_already_exists"
    RESOURCE_CONFLICT = "resource_conflict"
    RESOURCE_NOT_FOUND = "resource_not_found"

    # ------------------------------------------------------------------
    # Business Rule Errors
    # ------------------------------------------------------------------
    BUSINESS_RULE_VIOLATION = "business_rule_violation"
    OPERATION_NOT_ALLOWED = "operation_not_allowed"

    # ------------------------------------------------------------------
    # Infrastructure Errors
    # ------------------------------------------------------------------
    DATABASE_ERROR = "database_error"
    EXTERNAL_SERVICE_ERROR = "external_service_error"
    SERVICE_UNAVAILABLE = "service_unavailable"

    # ------------------------------------------------------------------
    # Internal Errors
    # ------------------------------------------------------------------
    INTERNAL_ERROR = "internal_error"
    UNKNOWN_ERROR = "unknown_error"
