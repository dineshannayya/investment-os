"""
Database session configuration.
"""

from sqlalchemy.orm import Session, sessionmaker

from app.core.database.engine import engine

#
# Internal session factory.
#
_SessionFactory = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


def create_session() -> Session:
    """
    Create a new SQLAlchemy session.

    The caller is responsible for closing the session.
    """

    return _SessionFactory()
