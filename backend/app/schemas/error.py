"""
Error response schemas.

This module defines the standard error model used throughout
Investment OS APIs.
"""

from __future__ import annotations

from pydantic import ConfigDict, Field

from app.core.config.error_codes import ErrorCode
from app.schemas.base import BaseSchema


class ErrorDetail(BaseSchema):
    """
    Represents a single application error.

    Multiple errors may be returned in a single API response,
    particularly for validation failures.
    """

    model_config = ConfigDict(
        **BaseSchema.model_config,
        update={
            "json_schema_extra": {
                "example": {
                    "code": "validation_error",
                    "message": "Email address is invalid.",
                    "field": "email",
                }
            }
        },
    )

    code: ErrorCode = Field(
        ...,
        description="Machine-readable application error code.",
        examples=[ErrorCode.VALIDATION_ERROR],
    )

    message: str = Field(
        ...,
        description="Human-readable error message.",
        examples=["Email address is invalid."],
    )

    field: str | None = Field(
        default=None,
        description="Field associated with the error, if applicable.",
        examples=["email"],
    )
