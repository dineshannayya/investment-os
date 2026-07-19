"""Investment OS backend application."""

from fastapi import FastAPI
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class AppMetadata:
    name: str
    version: str


APP_METADATA = AppMetadata(
    name="Investment OS",
    version="0.1.0",
)

def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
    )

    @app.get("/", tags=["System"])
    async def root() -> dict[str, str]:
        """Return basic application information."""
        return {
            "name": APP_NAME,
            "version": APP_VERSION,
            "status": "running",
        }

    @app.get("/health", tags=["System"])
    async def health() -> dict[str, str]:
        """Return application health status."""
        return {
            "status": "healthy",
        }

    return app


app = create_app()
