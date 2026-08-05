"""
Tests for User ORM model.
"""

from __future__ import annotations

from app.models.user import User


class TestUserModel:
    """Tests for User model."""

    def test_repr(self) -> None:
        user = User(
            email="admin@example.com",
            password_hash="hashed-password",
        )

        user.id = "12345678-1234-5678-1234-567812345678"
        user.is_active = True

        result = repr(user)

        assert "User(" in result
        assert "admin@example.com" in result
        assert "is_active=True" in result
