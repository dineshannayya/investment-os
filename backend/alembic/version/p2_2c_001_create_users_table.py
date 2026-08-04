"""Create users table.

Revision ID: p2_2c_001
Revises: p2_2b_001
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID


# Revision identifiers
revision: str = "p2_2c_001"
down_revision: str | None = "p2_2b_001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    """Create users table."""

    op.create_table(
        "users",

        # ---------------------------------------------------------------------
        # Identity
        # ---------------------------------------------------------------------

        sa.Column(
            "id",
            UUID(as_uuid=True),
            nullable=False,
            primary_key=True,
        ),

        sa.Column(
            "email",
            sa.String(length=255),
            nullable=False,
        ),

        sa.Column(
            "full_name",
            sa.String(length=255),
            nullable=True,
        ),

        # ---------------------------------------------------------------------
        # Authentication
        # ---------------------------------------------------------------------

        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=False,
        ),

        # ---------------------------------------------------------------------
        # Status
        # ---------------------------------------------------------------------

        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),

        sa.Column(
            "is_superuser",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        sa.Column(
            "email_verified",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),

        # ---------------------------------------------------------------------
        # Audit
        # ---------------------------------------------------------------------

        sa.Column(
            "last_login",
            sa.DateTime(timezone=True),
            nullable=True,
        ),

        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),

        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
    )

    # -------------------------------------------------------------------------
    # Constraints
    # -------------------------------------------------------------------------

    op.create_unique_constraint(
        "uq_users_email",
        "users",
        ["email"],
    )

    # -------------------------------------------------------------------------
    # Indexes
    # -------------------------------------------------------------------------

    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
    )

# =============================================================================
# Downgrade
# =============================================================================

def downgrade() -> None:
    """Drop users table."""

    op.drop_index(
        "ix_users_email",
        table_name="users",
    )

    op.drop_constraint(
        "uq_users_email",
        "users",
        type_="unique",
    )

    op.drop_table("users")

