"""
Repository layer.

Repositories provide database access for domain models.
Business logic belongs in the service layer.
"""

from app.repositories.base import Repository
from app.repositories.user_repository import UserRepository

__all__ = [
    "Repository",
    "UserRepository",
]
