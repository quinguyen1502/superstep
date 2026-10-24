"""LangGraph Agent Server API (`/api/lg`): threads and the runs started on them."""
from alembic import op
import sqlalchemy as sa

revision = "0036_agent_threads"
down_revision = "0035_chat_sessions"


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "agent_threads" not in tables:
        op.create_table("agent_threads", sa.Column("id", sa.Text(), primary_key=True), sa.Column("owner", sa.Text(), nullable=False),
                        sa.Column("token_id", sa.Text()), sa.Column("workflow_id", sa.Text()), sa.Column("meta", sa.Text()),
                        sa.Column("created", sa.Float(), nullable=False), sa.Column("updated", sa.Float(), nullable=False))
        op.create_index("ix_agent_threads_owner", "agent_threads", ["owner"])
        op.create_index("ix_agent_threads_token_id", "agent_threads", ["token_id"])
    if "agent_thread_runs" not in tables:
        op.create_table("agent_thread_runs", sa.Column("run_id", sa.Text(), primary_key=True), sa.Column("thread_id", sa.Text(), nullable=False),
                        sa.Column("meta", sa.Text()), sa.Column("created", sa.Float(), nullable=False))
        op.create_index("ix_agent_thread_runs_thread_id", "agent_thread_runs", ["thread_id"])


def downgrade():
    op.drop_table("agent_thread_runs"); op.drop_table("agent_threads")
