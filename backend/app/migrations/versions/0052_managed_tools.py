"""Managed MCP connection configuration and durable external write intents."""
from alembic import op
import sqlalchemy as sa

revision = "0052_managed_tools"
down_revision = "0051_chat_app_keys"


def upgrade():
    with op.batch_alter_table("mcp_servers") as batch:
        batch.add_column(sa.Column("adapter", sa.Text()))
        batch.add_column(sa.Column("settings", sa.Text()))
    op.create_table("mcp_operations",
        sa.Column("id", sa.Text(), primary_key=True), sa.Column("owner", sa.Text(), nullable=False),
        sa.Column("server_id", sa.Text(), nullable=False), sa.Column("key", sa.Text(), nullable=False),
        sa.Column("fingerprint", sa.Text(), nullable=False), sa.Column("tool", sa.Text(), nullable=False),
        sa.Column("configuration", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False), sa.Column("result", sa.Text()),
        sa.Column("created", sa.Float(), nullable=False), sa.Column("updated", sa.Float(), nullable=False))
    op.create_index("ix_mcp_operations_owner", "mcp_operations", ["owner"])
    op.create_index("ix_mcp_operations_server_id", "mcp_operations", ["server_id"])


def downgrade():
    op.drop_table("mcp_operations")
    with op.batch_alter_table("mcp_servers") as batch:
        batch.drop_column("settings")
        batch.drop_column("adapter")
