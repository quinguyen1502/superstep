"""Independent chat branches and durable edit intents (TASK-0229)."""
from alembic import op
import sqlalchemy as sa

revision = "0053_chat_edits"
down_revision = "0052_managed_tools"
branch_labels = depends_on = None


def upgrade():
    op.add_column("chat_sessions", sa.Column("revision", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("chat_sessions", sa.Column("source_session_id", sa.Text()))
    op.add_column("chat_sessions", sa.Column("source_turn_id", sa.Text()))
    op.add_column("chat_turns", sa.Column("inherited", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_table("chat_edits", sa.Column("id", sa.Text(), primary_key=True),
                    sa.Column("source_session_id", sa.Text(), nullable=False), sa.Column("operation_id", sa.Text(), nullable=False),
                    sa.Column("branch_id", sa.Text(), nullable=False, unique=True), sa.Column("run_id", sa.Text(), nullable=False),
                    sa.Column("body_hash", sa.Text(), nullable=False), sa.Column("message", sa.Text(), nullable=False),
                    sa.Column("attachments", sa.Text(), nullable=False),
                    sa.Column("claimed", sa.Boolean(), nullable=False, server_default=sa.false()),
                    sa.Column("created", sa.Float(), nullable=False))
    op.create_index("uq_chat_edit_intent", "chat_edits", ["source_session_id", "operation_id"], unique=True)


def downgrade():
    op.drop_table("chat_edits")
    op.drop_column("chat_turns", "inherited")
    for name in ("source_turn_id", "source_session_id", "revision"):
        op.drop_column("chat_sessions", name)
