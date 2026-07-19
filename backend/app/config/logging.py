import logging

from app.core.config import settings


def configure_logging() -> None:
    """
    Configure application logging.
    Safe to call multiple times.
    """
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        force=True,
    )
