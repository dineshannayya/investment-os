"""
Alembic environment configuration.

This module configures Alembic for online and offline migrations using the
application's SQLAlchemy metadata and database configuration.
"""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

# Import all ORM models so that they are registered with Base.metadata.
# Add new models here as they are introduced.
import app.models  # noqa: F401
from alembic import context
from app.core.config.settings import settings
from app.core.database.base import Base

# ---------------------------------------------------------------------
# Alembic configuration
# ---------------------------------------------------------------------

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Use the application's database URL.
config.set_main_option(
    "sqlalchemy.url",
    settings.database_url,
)

target_metadata = Base.metadata


# ---------------------------------------------------------------------
# Offline migrations
# ---------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""

    context.configure(
        url=str(settings.database_url),
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
        dialect_opts={
            "paramstyle": "named",
        },
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------
# Online migrations
# ---------------------------------------------------------------------


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""

    configuration = config.get_section(config.config_ini_section)

    assert configuration is not None

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
