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

from tests.fixtures.auth import (
    access_token,
    auth_headers,
    refresh_token,
)
from tests.fixtures.permission import (
    permission,
    permission_factory,
)
from tests.fixtures.responses import (
    error_response,
    paginated_response,
    success_response,
)
from tests.fixtures.role import role, role_factory
from tests.fixtures.user import (
    admin_user,
    inactive_user,
    user,
    user_factory,
    verified_user,
)
from tests.fixtures.user_role import (
    active_user_role,
    expired_user_role,
    user_role,
    user_role_factory,
)

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

    # UserRole
    "user_role",
    "user_role_factory",
    "active_user_role",
    "expired_user_role",

    # User
    "user",
    "user_factory",
    "admin_user",
    "inactive_user",
    "verified_user",
]
