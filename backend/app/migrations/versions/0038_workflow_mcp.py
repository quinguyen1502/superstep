"""Workflows exposed as MCP tools at /mcp (TASK-0114): an opt-in flag per workflow."""
from alembic import op
import sqlalchemy as sa

revision = "0038_workflow_mcp"
down_revision = "0037_langsmith"


def upgrade():
    if "mcp_enabled" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("workflows")}:
        with op.batch_alter_table("workflows") as b: b.add_column(sa.Column("mcp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table("workflows") as b: b.drop_column("mcp_enabled")
