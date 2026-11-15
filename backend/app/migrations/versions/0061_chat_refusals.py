"""Index for chat trigger refusals by status and time (admin Usage page, product gauges)."""
from alembic import op

revision = "0061_chat_refusals"
down_revision = "0060_run_usage"
branch_labels = depends_on = None


def upgrade():
    op.create_index("ix_chat_messages_status_created", "chat_messages", ["status", "created"])


def downgrade():
    op.drop_index("ix_chat_messages_status_created", table_name="chat_messages")
