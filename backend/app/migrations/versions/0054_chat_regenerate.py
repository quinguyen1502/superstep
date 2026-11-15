"""Persist revision action independently of source retention."""
from alembic import op
import sqlalchemy as sa

revision = "0054_chat_regenerate"
down_revision = "0053_chat_edits"
branch_labels = depends_on = None


def upgrade():
    op.add_column("chat_sessions", sa.Column("source_action", sa.Text()))


def downgrade():
    op.drop_column("chat_sessions", "source_action")
