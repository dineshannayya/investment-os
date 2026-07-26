"""
Database fixtures for pytest.

These fixtures provide:

- SQLAlchemy Engine
- Database schema creation
- Per-test transaction isolation
- SQLAlchemy Session

Every test executes inside its own transaction, which is rolled back
after the test completes.
"""

from __future__ import annotations

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import Session, sessionmaker

from app.models import Base

# =============================================================================
# Engine
# =============================================================================

@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    """
    Create SQLAlchemy engine.

    One engine is shared across the entire test session.
    """

    engine = create_engine(
        "sqlite:///:memory:",
        future=True,
        echo=False,
    )

    yield engine

    engine.dispose()


# =============================================================================
# Schema
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def create_schema(engine: Engine):
    """
    Create all database tables before tests.

    Drop them after the test session.
    """

    Base.metadata.create_all(engine)

    yield

    Base.metadata.drop_all(engine)


# =============================================================================
# Connection
# =============================================================================

@pytest.fixture
def connection(engine: Engine) -> Generator[Connection, None, None]:
    """
    Create a database connection.

    One connection per test.
    """

    connection = engine.connect()

    yield connection

    connection.close()


# =============================================================================
# Transaction
# =============================================================================

@pytest.fixture
def transaction(connection: Connection):
    """
    Start a transaction.

    Every test runs inside one transaction.
    """

    transaction = connection.begin()

    yield transaction

    transaction.rollback()


# =============================================================================
# Session
# =============================================================================

@pytest.fixture
def db_session(
    connection: Connection,
    transaction,
) -> Generator[Session, None, None]:
    """
    Return SQLAlchemy session.

    Bound to the test transaction.
    """

    SessionLocal = sessionmaker(
        bind=connection,
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
        future=True,
    )

    session = SessionLocal()

    yield session

    session.close()
