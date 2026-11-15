"""API triggers: workflow_tokens table + runs.source. Idempotent.

Revision ID: 0005_api_triggers
Revises: 0004_hitl
Create Date: 2026-10-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0005_api_triggers"
down_revision = "0004_hitl"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "workflow_tokens" not in insp.get_table_names():
        op.create_table("workflow_tokens",
            sa.Column("id", sa.Text, primary_key=True), sa.Column("workflow_id", sa.Text, nullable=False),
            sa.Column("owner", sa.Text, nullable=False), sa.Column("name", sa.Text),
            sa.Column("token_hash", sa.Text, nullable=False, unique=True), sa.Column("prefix", sa.Text),
            sa.Column("created", sa.Float), sa.Column("last_used", sa.Float), sa.Column("revoked", sa.Float))
        op.create_index("ix_workflow_tokens_workflow_id", "workflow_tokens", ["workflow_id"])
    if "source" not in {c["name"] for c in insp.get_columns("runs")}:
        with op.batch_alter_table("runs") as b: b.add_column(sa.Column("source", sa.Text))


def downgrade() -> None:
    with op.batch_alter_table("runs") as b: b.drop_column("source")
    op.drop_table("workflow_tokens")
