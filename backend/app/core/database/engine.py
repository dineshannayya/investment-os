"""
Database engine configuration.
"""

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url

from app.core.config.settings import settings


def create_db_engine(database_url: str | None = None) -> Engine:
    """
    Create a SQLAlchemy engine.

    Parameters
    ----------
    database_url:
        Optional override database URL.
    """

    url = database_url or settings.database_url

    kwargs = {
        "pool_pre_ping": True,
    }

    dialect = make_url(url).get_backend_name()

    if dialect != "sqlite":
        kwargs.update(
            {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_timeout": 30,
            }
        )

    return create_engine(url, **kwargs)


#
# Singleton engine used by the application.
#
engine: Engine = create_db_engine()
