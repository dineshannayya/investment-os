"""
Pagination response schemas.

This module defines the standard pagination metadata returned by
Investment OS APIs.
"""

from __future__ import annotations

from pydantic import Field

from app.schemas.base import BaseSchema


class PaginationMeta(BaseSchema):
    """
    Pagination metadata for collection responses.
    """

    page: int = Field(
        ...,
        ge=1,
        description="Current page number.",
        examples=[1],
    )

    per_page: int = Field(
        ...,
        ge=1,
        description="Number of items requested per page.",
        examples=[25],
    )

    total_items: int = Field(
        ...,
        ge=0,
        description="Total number of matching records.",
        examples=[153],
    )

    total_pages: int = Field(
        ...,
        ge=0,
        description="Total number of available pages.",
        examples=[7],
    )

    has_previous: bool = Field(
        ...,
        description="Whether a previous page exists.",
        examples=[False],
    )

    has_next: bool = Field(
        ...,
        description="Whether a next page exists.",
        examples=[True],
    )
