"""
Tests for UserRepository.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user import UserRepository


class TestUserRepository:
    """Tests for UserRepository."""


@pytest.fixture
def repository(db_session: Session) -> UserRepository:
    """Return UserRepository instance."""

    return UserRepository(db_session)


@pytest.fixture
def user(db_session: Session) -> User:
    """Create a sample user."""

    user = User(
        id=uuid4(),
        email="admin@example.com",
        password_hash="hashed-password",
        full_name="Administrator",
        is_active=True,
        is_superuser=True,
        email_verified=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


def test_exists_by_email(
    repository: UserRepository,
    user: User,
):
    """Existing email should be found."""

    assert repository.exists_by_email(
        user.email,
    )


def test_email_not_exists(
    repository: UserRepository,
):
    """Unknown email should not exist."""

    assert not repository.exists_by_email(
        "unknown@example.com",
    )


def test_get_active_user(
    repository: UserRepository,
    user: User,
):
    """Should return active user."""

    result = repository.get_active_by_email(
        user.email,
    )

    assert result is not None


def test_get_inactive_user_returns_none(
    repository: UserRepository,
    db_session: Session,
    user: User,
):
    """Inactive users should not be returned."""

    user.is_active = False

    db_session.flush()

    result = repository.get_active_by_email(
        user.email,
    )

    assert result is None


def test_is_superuser(
    repository: UserRepository,
    user: User,
):
    """Verify superuser lookup."""

    result = repository.get_by_email(
        user.email,
    )

    assert result.is_superuser


# ----------------------------------
#  TestQueries
# ----------------------------------
def test_get_by_id_found(
    repository: UserRepository,
    user: User,
):
    """Should return user by ID."""

    result = repository.get_by_id(user.id)

    assert result is not None
    assert result.id == user.id


def test_get_by_id_not_found(
    repository: UserRepository,
):
    """Unknown ID returns None."""

    assert repository.get_by_id(uuid4()) is None


def test_get_by_email_found(
    repository: UserRepository,
    user: User,
):
    """Should return user by email."""

    result = repository.get_by_email(
        user.email,
    )

    assert result is not None
    assert result.id == user.id
    assert result.email == user.email


def test_get_by_email_not_found(
    repository: UserRepository,
):
    """Unknown email returns None."""

    result = repository.get_by_email(
        "unknown@example.com",
    )

    assert result is None


def test_list_active(
    repository: UserRepository,
    user: User,
):
    users = repository.list_active()

    assert len(users) == 1
    assert users[0].id == user.id


def test_list_superusers(
    repository: UserRepository,
    user: User,
):
    users = repository.list_superusers()

    assert len(users) == 1
    assert users[0].is_superuser


def test_search_by_email(
    repository: UserRepository,
    user: User,
):
    users = repository.search("admin")

    assert len(users) == 1
    assert users[0].email == user.email


def test_search_by_name(
    repository: UserRepository,
    user: User,
):
    users = repository.search("Administrator")

    assert len(users) == 1
    assert users[0].full_name == user.full_name


# ----------------------------------
#
# ----------------------------------

def test_update_password(
    repository: UserRepository,
    user: User,
):
    repository.update_password(
        user,
        "new-password-hash",
    )

    assert user.password_hash == "new-password-hash"


def test_verify_email(
    repository: UserRepository,
    user: User,
):
    user.email_verified = False

    repository.verify_email(user)

    assert user.email_verified is True


# ----------------------------------
# TestPersistence
# ---------------------------------
def test_update_last_login(
    repository: UserRepository,
    user: User,
):
    """Should update last login timestamp."""

    before = user.last_login

    repository.update_last_login(user)

    assert user.last_login is not None

    if before is not None:
        assert user.last_login >= before

def test_repository_session(
    repository: UserRepository,
    db_session: Session,
):
    assert repository.session is db_session
