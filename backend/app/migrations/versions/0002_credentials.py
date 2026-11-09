"""Credentials table for encrypted LLM provider keys.

Idempotent: a SQLite file created by the raw-SQL PR #2 build already has this table and is adopted as-is.

Revision ID: 0002_credentials
Revises: 0001_initial
Create Date: 2026-10-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_credentials"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "credentials" in sa.inspect(op.get_bind()).get_table_names(): return
    op.create_table("credentials",
        sa.Column("id", sa.Text, primary_key=True), sa.Column("owner", sa.Text), sa.Column("name", sa.Text),
        sa.Column("provider", sa.Text), sa.Column("base_url", sa.Text), sa.Column("secret", sa.Text),
        sa.Column("hint", sa.Text), sa.Column("created", sa.Float))
    op.create_index("ix_credentials_owner", "credentials", ["owner"])


def downgrade() -> None:
    op.drop_table("credentials")
