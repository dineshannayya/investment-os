from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["System"])


@router.get("/")
async def root():

    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
        "status": "running",
    }


@router.get("/health")
async def health():

    return {
        "status": "healthy",
    }
