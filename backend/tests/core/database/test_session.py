"""
Tests for app.core.database.session.
"""

from sqlalchemy.orm import Session

from app.core.database.engine import engine
from app.core.database.session import create_session


def test_create_session_returns_session() -> None:
    """
    Verify create_session() returns a SQLAlchemy Session.
    """

    # Act
    session = create_session()

    # Assert
    assert isinstance(session, Session)

    # Cleanup
    session.close()


def test_create_session_returns_unique_sessions() -> None:
    """
    Verify each create_session() call returns a new Session.
    """

    # Act
    session1 = create_session()
    session2 = create_session()

    # Assert
    assert session1 is not session2

    # Cleanup
    session1.close()
    session2.close()


def test_session_is_bound_to_engine() -> None:
    """
    Verify session is bound to application Engine.
    """

    # Act
    session = create_session()

    # Assert
    assert session.bind is engine

    # Cleanup
    session.close()


def test_session_configuration() -> None:
    """
    Verify Session configuration.
    """

    # Act
    session = create_session()

    # Assert
    assert session.autoflush is False
    assert session.expire_on_commit is False

    # Cleanup
    session.close()


def test_session_close() -> None:
    """
    Verify Session.close() succeeds.
    """

    session = create_session()

    session.close()


def test_session_close_is_idempotent() -> None:
    """
    Verify Session.close() can be called multiple times.
    """

    session = create_session()

    session.close()
    session.close()
