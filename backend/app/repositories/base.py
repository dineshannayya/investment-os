"""
Base repository.
"""

from __future__ import annotations

from typing import TypeVar

from sqlalchemy.orm import Session

T = TypeVar("T")


class Repository:
    """
    Base class for all repositories.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, entity: T) -> T:
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def remove(self, entity: T) -> None:
        self._session.delete(entity)
        self._session.commit()
