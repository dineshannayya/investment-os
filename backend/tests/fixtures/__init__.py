"""
Reusable pytest fixtures for Investment OS.

This package centralizes reusable fixtures that can be imported into
tests/conftest.py.

Fixture modules should contain only fixture implementations.

Example:
    from tests.fixtures import (
        role,
        role_factory,
        permission,
        permission_factory,
    )
"""

from tests.fixtures.auth import *
from tests.fixtures.permission import *
from tests.fixtures.responses import *
from tests.fixtures.role import *

__all__ = [
    # Authentication
    "access_token",
    "refresh_token",
    "auth_headers",

    # Response fixtures
    "success_response",
    "error_response",
    "paginated_response",

    # Role
    "role",
    "role_factory",

    # Permission
    "permission",
    "permission_factory",
]
