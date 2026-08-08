"""
User repository.

Database access layer for User entities.
"""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.models.user import User
from app.repositories.base import Repository


class UserRepository(Repository):
    """
    Repository for User persistence operations.
    """

    # -------------------------------------------------------------------------
    # Queries
    #    ├── get_by_id()
    #    ├── get_by_email()
    #    ├── get_active_by_email()
    #    ├── exists_by_email()
    #    ├── list_active()
    #    ├── list_superusers()
    #    └── search()
    # -------------------------------------------------------------------------

    def get_by_id(
        self,
        user_id: UUID,
    ) -> User | None:
        """
        Return a user by ID.
        """

        stmt = select(User).where(User.id == user_id)

        return self._session.scalar(stmt)

    def get_by_email(
        self,
        email: str,
    ) -> User | None:
        """
        Return a user by email address.
        """

        stmt = (
            select(User)
            .where(User.email == email.lower())
        )

        return self._session.scalar(stmt)

    def get_active_by_email(
        self,
        email: str,
    ) -> User | None:
        """
        Return active user by email.
        """
    
        stmt = (
            select(User)
            .where(
                User.email == email.lower(),
                User.is_active.is_(True),
            )
        )
    
        return self._session.scalar(stmt)

    def exists_by_email(
        self,
        email: str,
    ) -> bool:
        """
        Check whether a user exists.
        """

        return self.get_by_email(email) is not None

    def list_active(
        self,
    ) -> list[User]:
        """
        Return all active users.
        """
    
        stmt = (
            select(User)
            .where(User.is_active.is_(True))
            .order_by(User.full_name)
        )
    
        return list(self._session.scalars(stmt))

    def list_superusers(
        self,
    ) -> list[User]:
        """
        Return all administrators.
        """
    
        stmt = (
            select(User)
            .where(User.is_superuser.is_(True))
            .order_by(User.full_name)
        )
    
        return list(self._session.scalars(stmt))


    def search(
        self,
        keyword: str,
    ) -> list[User]:
        """
        Search users by name or email.
        """
    
        pattern = f"%{keyword.lower()}%"
    
        stmt = (
            select(User)
            .where(
                User.email.ilike(pattern)
                | User.full_name.ilike(pattern)
            )
            .order_by(User.full_name)
        )
    
        return list(self._session.scalars(stmt))
    # -------------------------------------------------------------------------
    # Persistence
    #  CRUD
    #     ├── create()
    #     ├── update()
    #     └── delete()
    # -------------------------------------------------------------------------

    def create(
        self,
        user: User,
    ) -> User:
        """
        Persist a new user.
        """

        return self.save(user)

    def update(
        self,
        user: User,
    ) -> User:
        """
        Persist user changes.
        """

        return self.save(user)

    def delete(
        self,
        user: User,
    ) -> None:
        """
        Delete a user.
        """

        self.remove(user)

    # -------------------------------------------------------------------------
    # Authentication
    #   ├── touch_login()
    #   ├── update_password()
    #   └── verify_email()
    # -------------------------------------------------------------------------

    def update_last_login(
        self,
        user: User,
    ) -> User:
        """
        Update the user's last login timestamp.
        """

        user.last_login = datetime.now(UTC)

        return self.save(user)

    def update_password(
        self,
        user: User,
        password_hash: str,
    ) -> User:
        """
        Persist new password hash.
        """
    
        user.password_hash = password_hash
    
        return self.save(user)


    def verify_email(
        self,
        user: User,
    ) -> User:
        """
        Mark email as verified.
        """
    
        user.email_verified = True
    
        return self.save(user)



     
    # -------------------------------------------------------------------------
    # 
    # -------------------------------------------------------------------------




