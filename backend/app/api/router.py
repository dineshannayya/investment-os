from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.startups import router as startups_router
from app.api.system import router as system_router
from app.core.config import API_PREFIX
from app.api.founders import router as founders_router
from app.api.documents import router as documents_router

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

# -------------------------------------------------------------------------
# Founder Management
# -------------------------------------------------------------------------

api_router.include_router(founders_router)

# -------------------------------------------------------------------------
# Document Management
# -------------------------------------------------------------------------

api_router.include_router(documents_router)
