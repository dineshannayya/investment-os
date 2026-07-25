"""
Middleware registration.

This module defines the application's middleware pipeline.

IMPORTANT:
FastAPI/Starlette executes HTTP middleware in reverse registration order
(last registered = first executed).

The middleware list below is therefore arranged in logical request order
(top to bottom) and registered in reverse to preserve readability.

See:
    ADR-0102 – Middleware Architecture
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from starlette.responses import Response

from app.core.middleware.request_id import request_id_middleware
from app.core.middleware.request_logging import request_logging_middleware
from app.core.middleware.timing import timing_middleware

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

type CallNext = Callable[[Request], Awaitable[Response]]
type MiddlewareFunc = Callable[[Request, CallNext], Awaitable[Response]]

# ---------------------------------------------------------------------------
# Logical middleware pipeline
#
# Top -> Bottom == Request Flow
# ---------------------------------------------------------------------------

MIDDLEWARE_PIPELINE: tuple[MiddlewareFunc, ...] = (
    request_id_middleware,
    timing_middleware,
    request_logging_middleware,
)

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_middlewares(app: FastAPI) -> None:
    """
    Register all application middleware.

    Middleware are registered in reverse order because FastAPI executes
    middleware using LIFO semantics.

    Request execution:

        Request
            ↓
        Request ID
            ↓
        Timing
            ↓
        Request Logging
            ↓
        Router
            ↓
        Response
    """

    for middleware in reversed(MIDDLEWARE_PIPELINE):
        app.middleware("http")(middleware)
