"""chat messages that matched a chat trigger: dedupe, the run they started, where to reply."""
from alembic import op
import sqlalchemy as sa

revision = "0034_chat_messages"
down_revision = "0033_chat_triggers"


def upgrade():
    if "chat_messages" not in set(sa.inspect(op.get_bind()).get_table_names()):
        op.create_table("chat_messages", sa.Column("id", sa.Text(), primary_key=True), sa.Column("channel_id", sa.Text(), nullable=False),
                        sa.Column("key", sa.Text(), nullable=False), sa.Column("trigger_id", sa.Text(), index=True),
                        sa.Column("workflow_id", sa.Text(), nullable=False), sa.Column("kind", sa.Text(), nullable=False),
                        sa.Column("team", sa.Text(), nullable=False, server_default=""), sa.Column("sender", sa.Text(), nullable=False),
                        sa.Column("text", sa.Text(), nullable=False), sa.Column("ref", sa.Text(), nullable=False),
                        sa.Column("status", sa.Text(), nullable=False), sa.Column("code", sa.Text()),
                        sa.Column("run_id", sa.Text(), index=True), sa.Column("replied", sa.Text()), sa.Column("created", sa.Float(), nullable=False))
        op.create_index("uq_chat_messages_key", "chat_messages", ["channel_id", "key"], unique=True)


def downgrade():
    op.drop_index("uq_chat_messages_key", "chat_messages"); op.drop_table("chat_messages")
