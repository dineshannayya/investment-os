"""
Request ID middleware.

Creates a RequestContext for every incoming request.
"""

from uuid import uuid4

from fastapi import Request
from starlette.responses import Response

from app.core.logger import get_logger
from app.core.middleware.request_context import RequestContext

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"


async def request_id_middleware(
    request: Request,
    call_next,
) -> Response:
    """
    Create RequestContext for every request.
    """

    logger.debug(">>> REQUEST_ID ENTER")

    context = RequestContext(
        request_id=uuid4(),
        method=request.method,
        path=request.url.path,
    )

    request.state.context = context

    response = await call_next(request)

    logger.debug(">>> REQUEST_ID EXIT")

    response.headers[REQUEST_ID_HEADER] = str(context.request_id)

    return response
