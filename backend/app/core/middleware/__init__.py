from fastapi import FastAPI

from .request_id import request_id_middleware
from .request_logging import request_logging_middleware
from .timing import timing_middleware


def register_middlewares(app: FastAPI) -> None:
    """
    Register application middleware.
    """

    app.middleware("http")(request_logging_middleware)
    app.middleware("http")(timing_middleware)
    app.middleware("http")(request_id_middleware)
