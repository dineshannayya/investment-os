"""
Database health utilities.
"""

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.database.session import create_session


def is_database_alive() -> bool:
    """
    Verify database connectivity.
    """

    db = create_session()

    try:
        db.execute(text("SELECT 1"))
        return True

    except SQLAlchemyError:
        return False

    finally:
        db.close()
