"""
Tests for RBAC ORM relationships.
"""

from __future__ import annotations

from sqlalchemy import inspect

from app.models.permission import Permission
from app.models.role import Role
from app.models.role_permission import RolePermission
from app.models.user import User
from app.models.user_role import UserRole


class TestRBACRelationships:
    """Verify SQLAlchemy RBAC relationships."""

    def test_user_has_user_roles(self, user_role):
        """User exposes assigned roles."""

        assert user_role in user_role.user.user_roles

    def test_role_has_user_roles(self, user_role):
        """Role exposes assigned users."""

        assert user_role in user_role.role.user_roles

    def test_role_has_role_permissions(self, role_permission):
        """Role exposes granted permissions."""

        assert role_permission in role_permission.role.role_permissions

    def test_permission_has_role_permissions(self, role_permission):
        """Permission exposes assigned roles."""

        assert role_permission in (
            role_permission.permission.role_permissions
        )

    def test_user_role_bidirectional(self, user_role):
        """UserRole <-> User and Role are bidirectional."""

        assert user_role.user is not None
        assert user_role.role is not None

        assert user_role in user_role.user.user_roles
        assert user_role in user_role.role.user_roles

    def test_role_permission_bidirectional(
        self,
        role_permission,
    ):
        """RolePermission <-> Role and Permission are bidirectional."""

        assert role_permission.role is not None
        assert role_permission.permission is not None

        assert (
            role_permission
            in role_permission.role.role_permissions
        )

        assert (
            role_permission
            in role_permission.permission.role_permissions
        )

    def test_user_role_relationship_loading(self):
        """User.user_roles uses selectin loading."""

        rel = inspect(User).relationships.user_roles
        assert rel.lazy == "selectin"

    def test_role_user_roles_loading(self):
        """Role.user_roles uses selectin loading."""

        rel = inspect(Role).relationships.user_roles
        assert rel.lazy == "selectin"

    def test_role_permission_loading(self):
        """Role.role_permissions uses selectin loading."""

        rel = inspect(Role).relationships.role_permissions
        assert rel.lazy == "selectin"

    def test_permission_loading(self):
        """Permission.role_permissions uses selectin loading."""

        rel = inspect(Permission).relationships.role_permissions
        assert rel.lazy == "selectin"

    def test_mapper_configuration(self):
        """Verify SQLAlchemy mapper configuration."""

        inspect(User)
        inspect(Role)
        inspect(Permission)
        inspect(UserRole)
        inspect(RolePermission)

    def test_audit_relationships_are_available(
        self,
        user_role,
        role_permission,
    ):
        """Audit relationships remain accessible."""
    
        assert user_role.assigned_by_user is None or (
            user_role.assigned_by_user.id == user_role.assigned_by
        )
    
        assert role_permission.granted_by_user is None or (
            role_permission.granted_by_user.id == role_permission.granted_by
        )

