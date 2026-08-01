"""
API response factory.

Provides factory methods for creating consistent API responses
throughout Investment OS.
"""

from __future__ import annotations

from typing import TypeVar

from app.core.config.error_codes import ErrorCode
from app.schemas.error import ErrorDetail
from app.schemas.pagination import PaginationMeta
from app.schemas.response import ApiResponse, ResponseMeta

T = TypeVar("T")


class ResponseFactory:
    """Factory for constructing standard API responses."""

    @classmethod
    def success(
        cls,
        *,
        data: T | None = None,
        message: str = "Request completed successfully.",
        request_id: str | None = None,
    ) -> ApiResponse[T]:
        return ApiResponse(
            success=True,
            message=message,
            data=data,
            meta=ResponseMeta(
                request_id=request_id,
            ),
        )

    @classmethod
    def created(
        cls,
        *,
        data: T,
        message: str = "Resource created successfully.",
        request_id: str | None = None,
    ) -> ApiResponse[T]:
        return ApiResponse(
            success=True,
            message=message,
            data=data,
            meta=ResponseMeta(
                request_id=request_id,
            ),
        )

    @classmethod
    def paginated(
        cls,
        *,
        data: T,
        pagination: PaginationMeta,
        message: str = "Request completed successfully.",
        request_id: str | None = None,
    ) -> ApiResponse[T]:
        return ApiResponse(
            success=True,
            message=message,
            data=data,
            meta=ResponseMeta(
                request_id=request_id,
                pagination=pagination,
            ),
        )

    @classmethod
    def error(
        cls,
        *,
        code: ErrorCode,
        message: str,
        field: str | None = None,
        request_id: str | None = None,
    ) -> ApiResponse[None]:
        return ApiResponse(
            success=False,
            message=message,
            data=None,
            meta=ResponseMeta(
                request_id=request_id,
            ),
            errors=[
                ErrorDetail(
                    code=code,
                    message=message,
                    field=field,
                )
            ],
        )
