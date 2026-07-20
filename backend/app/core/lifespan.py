from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.
    """

    logger.info(
        "Starting %s v%s",
        settings.app_name,
        settings.app_version,
    )

    #
    # Future initialization
    #
    # await database.connect()
    # await redis.connect()
    # load_models()
    #

    yield

    logger.info("Stopping %s", settings.app_name)

    #
    # Future cleanup
    #
    # await database.disconnect()
    # await redis.disconnect()
    #
