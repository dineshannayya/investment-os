"""
Request logging middleware.
"""

from fastapi import Request
from starlette.responses import Response

from app.core.logger import get_logger

logger = get_logger(__name__)


async def request_logging_middleware(
    request: Request,
    call_next,
) -> Response:
    """
    Log every request.
    """

    try:
        response = await call_next(request)
        return response

    finally:
        context = getattr(request.state, "context", None)

        if context is not None:
            if context.exception is None:
                logger.info(
                    "%s %s status=%s duration=%.3fms request_id=%s",
                    context.method,
                    context.path,
                    context.status_code,
                    context.duration_ms or 0.0,
                    context.request_id,
                )
            else:
                logger.exception(
                    "%s %s status=%s duration=%.3fms request_id=%s",
                    context.method,
                    context.path,
                    context.status_code or 500,
                    context.duration_ms or 0.0,
                    context.request_id,
                    exc_info=context.exception,
                )
