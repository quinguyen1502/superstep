"""One rating per chat answer (TASK-0162, REQ-0075, DEC-0070)."""
from alembic import op
import sqlalchemy as sa

revision = "0042_chat_ratings"
down_revision = "0041_chat_logos"


def upgrade():
    if "chat_ratings" in sa.inspect(op.get_bind()).get_table_names(): return
    op.create_table("chat_ratings",
                    sa.Column("turn_id", sa.Text(), primary_key=True),
                    sa.Column("session_id", sa.Text(), nullable=False),
                    sa.Column("workflow_id", sa.Text(), nullable=False),
                    sa.Column("value", sa.Text(), nullable=False),
                    sa.Column("comment", sa.Text(), nullable=False, server_default=""),
                    sa.Column("feedback_id", sa.Text(), nullable=False, server_default=""),
                    sa.Column("created", sa.Float(), nullable=False),
                    sa.Column("updated", sa.Float(), nullable=False))
    op.create_index("ix_chat_ratings_session_id", "chat_ratings", ["session_id"])
    op.create_index("ix_chat_ratings_workflow_updated", "chat_ratings", ["workflow_id", "updated"])


def downgrade():
    op.drop_index("ix_chat_ratings_workflow_updated", table_name="chat_ratings")
    op.drop_index("ix_chat_ratings_session_id", table_name="chat_ratings")
    op.drop_table("chat_ratings")
