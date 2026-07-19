"""Investment OS backend application."""

from fastapi import FastAPI
from app.core.config import settings


from app.config.logging import configure_logging
from app.core.logger import get_logger

configure_logging()

logger = get_logger(__name__)

def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    """

    logger.info("Creating FastAPI application")

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        debug=settings.debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    logger.info(
        "Application initialized: %s v%s",
        settings.app_name,
        settings.app_version,
    )

    # ------------------------------------------------------------------
    # Root Endpoint
    # ------------------------------------------------------------------
    @app.get("/", tags=["System"])
    async def root() -> dict[str, str]:
        """
        Return basic application information.
        """
        return {
            "application": settings.app_name,
            "version": settings.app_version,
            "environment": settings.app_env,
            "status": "running",
        }

    # ------------------------------------------------------------------
    # Health Check
    # ------------------------------------------------------------------
    @app.get("/health", tags=["System"])
    async def health() -> dict[str, str]:
        """
        Basic health endpoint.
        """
        return {
            "status": "healthy",
        }

    return app


app = create_app()
