"""The agent that answered a chat session last (TASK-0181, REQ-0078, DEC-0073 decision 4)."""
from alembic import op
import sqlalchemy as sa

revision = "0045_chat_active_agent"
down_revision = "0044_chat_attachments"


def upgrade():
    if "active_agent" in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("chat_sessions")}: return
    with op.batch_alter_table("chat_sessions") as b: b.add_column(sa.Column("active_agent", sa.Text()))


def downgrade():
    with op.batch_alter_table("chat_sessions") as b: b.drop_column("active_agent")
