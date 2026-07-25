"""
Request ID middleware.

Creates a RequestContext for every incoming request.
"""

from uuid import uuid4

from fastapi import Request
from starlette.responses import Response

from app.core.middleware.request_context import RequestContext

REQUEST_ID_HEADER = "X-Request-ID"


async def request_id_middleware(
    request: Request,
    call_next,
) -> Response:
    """
    Create RequestContext for every request.
    """

    context = RequestContext(
        request_id=uuid4(),
        method=request.method,
        path=request.url.path,
    )

    request.state.context = context

    response = await call_next(request)

    response.headers[REQUEST_ID_HEADER] = str(context.request_id)

    return response
