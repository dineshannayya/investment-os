"""
Base declarative model.

Re-export the application's shared SQLAlchemy Base.
"""

from app.core.database.base import Base

__all__ = ["Base"]
