"""
Tests for SQLAlchemy Declarative Base.
"""

from sqlalchemy import Column, Integer, MetaData, Table
from sqlalchemy.orm import DeclarativeBase

from app.models.base import Base


def test_base_is_declarative_base():
    assert issubclass(Base, DeclarativeBase)


def test_base_has_metadata():
    assert isinstance(Base.metadata, MetaData)


def test_base_metadata_exists():
    assert Base.metadata is not None


def test_can_register_table():

    metadata = MetaData()

    table = Table(
        "dummy",
        metadata,
        Column("id", Integer, primary_key=True),
    )

    assert table.name == "dummy"


def test_metadata_is_singleton():

    metadata1 = Base.metadata
    metadata2 = Base.metadata

    assert metadata1 is metadata2
