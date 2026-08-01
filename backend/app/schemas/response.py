"""
Generic API response schemas.

This module defines the standard response envelope used by all
Investment OS APIs.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import Field

from app.schemas.base import BaseSchema
from app.schemas.error import ErrorDetail
from app.schemas.pagination import PaginationMeta


class ResponseMeta(BaseSchema):
    """
    Metadata associated with an API response.
    """

    request_id: str | None = Field(
        default=None,
        description="Unique request identifier.",
    )

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp when the response was generated.",
    )

    pagination: PaginationMeta | None = Field(
        default=None,
        description="Pagination metadata.",
    )


class ApiResponse[T](BaseSchema):
    """
    Standard API response envelope.
    """

    success: bool = Field(
        ...,
        description="True if the request completed successfully.",
    )

    message: str = Field(
        ...,
        description="Human-readable response message.",
    )

    data: T | None = Field(
        default=None,
        description="Business response payload.",
    )

    meta: ResponseMeta | None = Field(
        default=None,
        description="Additional response metadata.",
    )

    errors: list[ErrorDetail] = Field(
        default_factory=list,
        description="List of application errors.",
    )
