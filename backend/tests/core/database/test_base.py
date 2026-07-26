"""
Unit tests for app.core.database.base.
"""

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.core.database.base import Base


def test_base_is_declarative_base() -> None:
    """
    Verify Base inherits from SQLAlchemy DeclarativeBase.
    """

    assert issubclass(Base, DeclarativeBase)

def test_models_share_base_metadata() -> None:
    """
    Verify models derived from Base share the same metadata.
    """

    class DummyModel(Base):
        __tablename__ = "dummy"

        id: Mapped[int] = mapped_column(primary_key=True)

    assert DummyModel.metadata is Base.metadata

def test_base_has_metadata() -> None:
    """
    Verify Base exposes SQLAlchemy metadata.
    """

    assert Base.metadata is not None
