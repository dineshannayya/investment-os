"""Investment OS backend application."""

from fastapi import FastAPI

from app.api.router import api_router
from app.config.logging import configure_logging
from app.core.config import settings
from app.core.lifespan import lifespan

configure_logging()


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.include_router(api_router)

    return app


app = create_app()
