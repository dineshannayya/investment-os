"""
Unit tests for app.core.database.health.
"""

from unittest.mock import MagicMock, patch

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.database.health import is_database_alive


def test_database_alive_returns_true() -> None:
    """
    Verify healthy database returns True.
    """

    # Arrange
    mock_session = MagicMock(spec=Session)

    with patch(
        "app.core.database.health.create_session",
        return_value=mock_session,
    ):

        # Act
        result = is_database_alive()

        # Assert
        assert result is True

        mock_session.execute.assert_called_once()

        mock_session.close.assert_called_once()


def test_database_alive_returns_false_on_database_error() -> None:
    """
    Verify SQLAlchemyError returns False.
    """

    # Arrange
    mock_session = MagicMock(spec=Session)

    mock_session.execute.side_effect = SQLAlchemyError()

    with patch(
        "app.core.database.health.create_session",
        return_value=mock_session,
    ):

        # Act
        result = is_database_alive()

        # Assert
        assert result is False

        mock_session.execute.assert_called_once()

        mock_session.close.assert_called_once()


def test_database_alive_executes_select_one_query() -> None:
    """
    Verify expected SQL health check is executed.
    """

    # Arrange
    mock_session = MagicMock(spec=Session)

    with patch(
        "app.core.database.health.create_session",
        return_value=mock_session,
    ):

        # Act
        is_database_alive()

        # Assert
        statement = mock_session.execute.call_args.args[0]

        assert str(statement) == "SELECT 1"
