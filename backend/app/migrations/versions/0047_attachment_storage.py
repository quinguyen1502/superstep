"""Chat attachment storage (TASK-0191, REQ-0080, DEC-0074): where a row's bytes are."""
from alembic import op
import sqlalchemy as sa

revision = "0047_attachment_storage"
down_revision = "0046_auto_approval"


def upgrade():
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("chat_attachments")}
    with op.batch_alter_table("chat_attachments") as b:
        if "storage" not in cols: b.add_column(sa.Column("storage", sa.Text(), nullable=False, server_default="db"))
        if "key" not in cols: b.add_column(sa.Column("key", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("chat_attachments") as b:
        b.drop_column("key"); b.drop_column("storage")
