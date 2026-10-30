"""Chat attachments (TASK-0174, REQ-0077, DEC-0072): the files of a chat message, in the database."""
from alembic import op
import sqlalchemy as sa

revision = "0044_chat_attachments"
down_revision = "0043_personal_access_tokens"


def upgrade():
    if "chat_attachments" in sa.inspect(op.get_bind()).get_table_names(): return
    op.create_table("chat_attachments",
                    sa.Column("id", sa.Text(), primary_key=True),
                    sa.Column("session_id", sa.Text(), nullable=False),
                    sa.Column("turn_id", sa.Text()),
                    sa.Column("name", sa.Text(), nullable=False),
                    sa.Column("kind", sa.Text(), nullable=False),
                    sa.Column("mime", sa.Text(), nullable=False),
                    sa.Column("size", sa.Integer(), nullable=False),
                    sa.Column("data", sa.LargeBinary(), nullable=False),
                    sa.Column("text", sa.Text()),
                    sa.Column("text_cut", sa.Boolean(), nullable=False, server_default=sa.false()),
                    sa.Column("created", sa.Float(), nullable=False))
    op.create_index("ix_chat_attachments_session_turn", "chat_attachments", ["session_id", "turn_id"])
    op.create_index("ix_chat_attachments_created", "chat_attachments", ["created"])


def downgrade():
    op.drop_table("chat_attachments")
