"""
Global exception handlers.

Registers FastAPI exception handlers for application and framework
exceptions.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.config.error_codes import ErrorCode
from app.core.exceptions import AppException
from app.core.response import ResponseFactory

logger = logging.getLogger(__name__)


async def app_exception_handler(
    request: Request,
    exc: AppException,
) -> JSONResponse:
    """
    Handle all application exceptions.
    """

    logger.warning(
        "%s: %s",
        exc.code,
        exc.message,
    )

    response = ResponseFactory.error(
        code=exc.code,
        message=exc.message,
        field=exc.field,
        request_id=getattr(request.state, "request_id", None),
    )

    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump(mode="json"),
    )


async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle FastAPI request validation errors.
    """

    errors = []

    for error in exc.errors():
        location = ".".join(str(item) for item in error["loc"])
        errors.append(
            {
                "code": ErrorCode.VALIDATION_ERROR,
                "message": error["msg"],
                "field": location,
            }
        )

    response = ResponseFactory.error(
        code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed.",
        request_id=getattr(request.state, "request_id", None),
    )

    response.errors = errors

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=response.model_dump(mode="json"),
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Handle unexpected exceptions.
    """

    logger.exception("Unhandled exception", exc_info=exc)

    response = ResponseFactory.error(
        code=ErrorCode.INTERNAL_ERROR,
        message="Internal server error.",
        request_id=getattr(request.state, "request_id", None),
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=response.model_dump(mode="json"),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register all exception handlers.
    """

    app.add_exception_handler(
        AppException,
        app_exception_handler,
    )

    app.add_exception_handler(
        RequestValidationError,
        validation_exception_handler,
    )

    app.add_exception_handler(
        Exception,
        unhandled_exception_handler,
    )
