from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.schemas.auth import AuthenticatedUser


@pytest.fixture
def authenticated_user() -> AuthenticatedUser:
    """Return a sample authenticated administrator."""
    return AuthenticatedUser(
        id=uuid4(),
        email="admin@example.com",
        full_name="Administrator",
        is_active=True,
        is_superuser=True,
        email_verified=True,
        last_login=None,
    )


# tests/fixtures/auth.py

@pytest.fixture
def mock_auth_service() -> MagicMock:
    """Mock authentication service."""
    return MagicMock()
