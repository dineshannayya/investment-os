"""
Unit tests for app.core.database.dependencies.

Tests the FastAPI database dependency lifecycle.
"""

from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.core.database.dependencies import get_db


def test_get_db_yields_session() -> None:
    """
    Verify get_db() yields the created Session.
    """

    # Arrange
    mock_session = MagicMock(spec=Session)

    with patch(
        "app.core.database.dependencies.create_session",
        return_value=mock_session,
    ) as mock_create_session:

        # Act
        generator = get_db()
        session = next(generator)

        # Assert
        assert session is mock_session

        mock_create_session.assert_called_once()

        # Cleanup
        generator.close()


def test_get_db_closes_session_after_iteration() -> None:
    """
    Verify Session.close() is called after generator completes.
    """

    # Arrange
    mock_session = MagicMock(spec=Session)

    with patch(
        "app.core.database.dependencies.create_session",
        return_value=mock_session,
    ):

        # Act
        generator = get_db()

        next(generator)

        with pytest.raises(StopIteration):
            next(generator)

        # Assert
        mock_session.close.assert_called_once()

def test_get_db_closes_session_on_exception() -> None:
    """
    Verify Session.close() is called when an exception is thrown
    into the dependency generator.
    """

    # Arrange
    mock_session = MagicMock(spec=Session)

    with patch(
        "app.core.database.dependencies.create_session",
        return_value=mock_session,
    ):

        generator = get_db()

        next(generator)

        # Act / Assert
        with pytest.raises(RuntimeError):
            generator.throw(RuntimeError("boom"))

        mock_session.close.assert_called_once()



