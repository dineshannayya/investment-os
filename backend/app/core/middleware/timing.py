"""
Request timing middleware.
"""

from time import perf_counter

from fastapi import Request
from starlette.responses import Response

from app.core.logger import get_logger

logger = get_logger(__name__)

async def timing_middleware(
    request: Request,
    call_next,
) -> Response:
    """
    Measure request execution time.
    """

    # timing_middleware requires RequestContext created by
    # request_id_middleware. If the context is absent,
    # timing collection is skipped.
    context = getattr(request.state, "context", None)

    if context is None:
        return await call_next(request)

    response = None

    logger.info(">>> TIMING ENTER")
    try:
        response = await call_next(request)
        logger.info(">>> TIMING EXIT")
        return response

    except Exception as exc:
        context.exception = exc
        raise

    finally:
        elapsed = (perf_counter() - context.start_time) * 1000
        context.duration_ms = round(elapsed, 3)

        if response is not None:
            context.status_code = response.status_code
            response.headers["X-Response-Time"] = f"{context.duration_ms:.3f} ms"
