from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.startups import router as startups_router
from app.api.system import router as system_router
from app.core.config import API_PREFIX

api_router = APIRouter(prefix=API_PREFIX)

# -------------------------------------------------------------------------
# System
# -------------------------------------------------------------------------

api_router.include_router(system_router)

# -------------------------------------------------------------------------
# Authentication
# -------------------------------------------------------------------------

api_router.include_router(auth_router)

# -------------------------------------------------------------------------
# Startup Management
# -------------------------------------------------------------------------

api_router.include_router(startups_router)
