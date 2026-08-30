"""
add_source_extractions_table

Revision ID: 1a7777ea5105
Revises: ff1b6d4c1d1b
Create Date: 2026-08-29 11:46:56.270736+00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

from sqlalchemy.dialects import postgresql


# ---------------------------------------------------------------------------
# Alembic Revision Identifiers
# ---------------------------------------------------------------------------

revision = "1a7777ea5105"
down_revision = "ff1b6d4c1d1b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Apply database schema changes."""

    op.create_table(
        "source_extractions",

        sa.Column(
            "id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "source_id",
            sa.UUID(),
            nullable=False,
        ),

        sa.Column(
            "source_sha256",
            sa.String(length=64),
            nullable=False,
        ),

        sa.Column(
            "status",
            sa.String(length=32),
            nullable=False,
        ),

        sa.Column(
            "extraction_method",
            sa.String(length=32),
            nullable=False,
        ),

        sa.Column(
            "processor_name",
            sa.String(length=128),
            nullable=False,
        ),

        sa.Column(
            "title",
            sa.String(length=512),
            nullable=True,
        ),

        sa.Column(
            "page_count",
            sa.Integer(),
            nullable=True,
        ),

        sa.Column(
            "text",
            sa.Text(),
            nullable=False,
        ),

        sa.Column(
            "segments",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),

        sa.Column(
            "quality",
            sa.String(length=16),
            nullable=False,
        ),

        sa.Column(
            "quality_warnings",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),

        sa.Column(
            "fallback_used",
            sa.Boolean(),
            nullable=False,
        ),

        sa.Column(
            "fallback_reason",
            sa.String(length=128),
            nullable=True,
        ),

        sa.Column(
            "extraction_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
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

        sa.PrimaryKeyConstraint(
            "id",
        ),

        sa.UniqueConstraint(
            "source_id",
            "source_sha256",
            name="uq_source_extractions_source_version",
        ),
    )

    op.create_index(
        op.f("ix_source_extractions_source_id"),
        "source_extractions",
        ["source_id"],
        unique=False,
    )


def downgrade() -> None:
    """Revert database schema changes."""

    op.drop_index(
        op.f("ix_source_extractions_source_id"),
        table_name="source_extractions",
    )

    op.drop_table(
        "source_extractions",
    )
