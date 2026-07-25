from fastapi import APIRouter

from app.core.config import settings
from app.schemas.system import (
    HealthResponse,
    ReadyResponse,
    ReadyServices,
    VersionResponse,
)

router = APIRouter(tags=["System"])


@router.get(
    "/health",
    response_model=HealthResponse,
)
async def health() -> HealthResponse:
    """
    Liveness endpoint.
    """

    return HealthResponse(
        status="ok",
    )


@router.get(
    "/ready",
    response_model=ReadyResponse,
)
async def ready() -> ReadyResponse:
    """
    Readiness endpoint.
    """

    return ReadyResponse(
        status="ready",
        services=ReadyServices(
            database="not_configured",
            redis="not_configured",
            llm="not_configured",
        ),
    )


@router.get(
    "/version",
    response_model=VersionResponse,
)
async def version() -> VersionResponse:
    """
    Application version.
    """

    return VersionResponse(
        application=settings.app_name,
        version=settings.app_version,
        environment=settings.environment,
    )
