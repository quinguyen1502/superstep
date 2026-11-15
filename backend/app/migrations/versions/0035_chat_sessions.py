"""web chat: chat sessions and turns, and the web chat trigger's settings."""
from alembic import op
import sqlalchemy as sa

revision = "0035_chat_sessions"
down_revision = "0034_chat_messages"


def upgrade():
    insp = sa.inspect(op.get_bind()); tables = set(insp.get_table_names())
    if "settings" not in {c["name"] for c in insp.get_columns("workflow_chat_triggers")}:
        with op.batch_alter_table("workflow_chat_triggers") as b: b.add_column(sa.Column("settings", sa.Text()))
    if "chat_sessions" not in tables:
        op.create_table("chat_sessions", sa.Column("id", sa.Text(), primary_key=True), sa.Column("workflow_id", sa.Text(), nullable=False),
                        sa.Column("trigger_id", sa.Text(), nullable=False), sa.Column("channel", sa.Text(), nullable=False, server_default="studio"),
                        sa.Column("owner", sa.Text()), sa.Column("visitor", sa.Text()), sa.Column("title", sa.Text(), nullable=False, server_default=""),
                        sa.Column("last_run_id", sa.Text()), sa.Column("created", sa.Float(), nullable=False), sa.Column("updated", sa.Float(), nullable=False))
        op.create_index("ix_chat_sessions_workflow_owner", "chat_sessions", ["workflow_id", "owner"])
        op.create_index("ix_chat_sessions_updated", "chat_sessions", ["updated"])
    if "chat_turns" not in tables:
        op.create_table("chat_turns", sa.Column("id", sa.Text(), primary_key=True), sa.Column("session_id", sa.Text(), nullable=False),
                        sa.Column("run_id", sa.Text()), sa.Column("role", sa.Text(), nullable=False), sa.Column("text", sa.Text(), nullable=False, server_default=""),
                        sa.Column("status", sa.Text(), nullable=False, server_default="ok"), sa.Column("node", sa.Text()), sa.Column("answered_by", sa.Text()),
                        sa.Column("code", sa.Text()), sa.Column("attachments", sa.Text()), sa.Column("created", sa.Float(), nullable=False))
        op.create_index("ix_chat_turns_session_id", "chat_turns", ["session_id"])
        op.create_index("ix_chat_turns_run_id", "chat_turns", ["run_id"])


def downgrade():
    op.drop_table("chat_turns"); op.drop_table("chat_sessions")
    with op.batch_alter_table("workflow_chat_triggers") as b: b.drop_column("settings")
