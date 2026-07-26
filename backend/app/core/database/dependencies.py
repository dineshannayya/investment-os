"""
Database dependency injection.

FastAPI dependencies for database access.
"""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.core.database.session import create_session

type SessionDependency = Generator[Session, None, None]


def get_db() -> SessionDependency:
    """
    FastAPI dependency.

    Creates one SQLAlchemy Session per request and
    guarantees cleanup.
    """

    db = create_session()

    try:
        yield db

    finally:
        db.close()
