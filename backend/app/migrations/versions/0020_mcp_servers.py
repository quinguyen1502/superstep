"""registry of MCP servers (stdio / Streamable HTTP) with encrypted secrets and cached tool lists."""
from alembic import op
import sqlalchemy as sa

revision = "0020_mcp_servers"
down_revision = "0019_knowledge_bases"


def upgrade():
    if "mcp_servers" in sa.inspect(op.get_bind()).get_table_names(): return
    op.create_table("mcp_servers",
        sa.Column("id", sa.Text(), primary_key=True), sa.Column("owner", sa.Text(), nullable=False, index=True),
        sa.Column("scope", sa.Text(), nullable=False, server_default="user"), sa.Column("name", sa.Text(), nullable=False),
        sa.Column("transport", sa.Text(), nullable=False), sa.Column("command", sa.Text()), sa.Column("args", sa.Text()),
        sa.Column("url", sa.Text()), sa.Column("secrets", sa.Text()), sa.Column("secret_hints", sa.Text()),
        sa.Column("tools", sa.Text()), sa.Column("tools_at", sa.Float()), sa.Column("created", sa.Float(), nullable=False))


def downgrade():
    op.drop_table("mcp_servers")
