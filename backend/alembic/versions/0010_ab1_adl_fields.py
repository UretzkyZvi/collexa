"""add adl_version and blueprint fields to agents

Revision ID: 0010_ab1_adl_fields
Revises: 0009_previous
Create Date: 2025-08-29
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "0010_ab1_adl_fields"
down_revision = "0009_previous"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agents", sa.Column("adl_version", sa.String(), nullable=True))
    op.add_column("agents", sa.Column("blueprint_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("agents", sa.Column("instructions_pack_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    # Optional manifest storage for MVP
    op.add_column("agents", sa.Column("manifest_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    op.drop_column("agents", "manifest_json")
    op.drop_column("agents", "instructions_pack_json")
    op.drop_column("agents", "blueprint_json")
    op.drop_column("agents", "adl_version")

