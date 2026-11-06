"""Add conversation_id for cross-turn browser sessions (TASK-0245 / DEC-0085)."""
from alembic import op
import sqlalchemy as sa

revision = "0057_browser_conversation_sessions"
down_revision = "0056_browser_sessions"
branch_labels = depends_on = None


def upgrade():
    with op.batch_alter_table("browser_sessions") as batch:
        batch.add_column(sa.Column("conversation_id", sa.Text(), nullable=True))
    op.create_index("ix_browser_sessions_conversation_id", "browser_sessions", ["conversation_id"])


def downgrade():
    op.drop_index("ix_browser_sessions_conversation_id", table_name="browser_sessions")
    with op.batch_alter_table("browser_sessions") as batch:
        batch.drop_column("conversation_id")
