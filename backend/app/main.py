"""Investment OS backend application."""

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import (
    DOCS_URL,
    OPENAPI_URL,
    REDOC_URL,
    settings,
)
from app.core.exception_handlers import register_exception_handlers
from app.core.lifespan import lifespan
from app.core.logging import configure_logging
from app.core.middleware import register_middlewares

configure_logging()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url=DOCS_URL,
        redoc_url=REDOC_URL,
        openapi_url=OPENAPI_URL,
        lifespan=lifespan,
    )

    register_middlewares(app)

    register_exception_handlers(app)

    app.include_router(api_router)

    return app


app = create_app()
