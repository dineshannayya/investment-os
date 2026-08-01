from fastapi import APIRouter

from app.api.system import router as system_router
from app.core.config import (
    API_PREFIX,
)

api_router = APIRouter(prefix=API_PREFIX)

api_router.include_router(system_router)
