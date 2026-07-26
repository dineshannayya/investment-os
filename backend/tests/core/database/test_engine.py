"""
Tests for app.core.database.engine.
"""

from sqlalchemy import Engine

from app.core.database.engine import create_db_engine, engine


def test_create_db_engine_returns_engine() -> None:
    """
    Verify create_db_engine() returns a SQLAlchemy Engine.
    """

    # Arrange
    database_url = "sqlite:///:memory:"

    # Act
    db_engine = create_db_engine(database_url)

    # Assert
    assert isinstance(db_engine, Engine)


def test_create_db_engine_uses_custom_database_url() -> None:
    """
    Verify custom database URL is honored.
    """

    # Arrange
    database_url = "sqlite:///:memory:"

    # Act
    db_engine = create_db_engine(database_url)

    # Assert
    assert str(db_engine.url) == database_url


def test_create_db_engine_returns_new_instance() -> None:
    """
    Verify every factory call creates a new Engine.
    """

    # Arrange
    database_url = "sqlite:///:memory:"

    # Act
    engine1 = create_db_engine(database_url)
    engine2 = create_db_engine(database_url)

    # Assert
    assert engine1 is not engine2


def test_engine_singleton_exists() -> None:
    """
    Verify module singleton is initialized.
    """

    assert engine is not None
    assert isinstance(engine, Engine)


def test_engine_has_required_components() -> None:
    """
    Verify engine contains required SQLAlchemy components.
    """

    assert engine.pool is not None
    assert engine.dialect is not None
