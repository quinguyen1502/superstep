"""A published chat's logo (TASK-0145, REQ-0074): one image per web chat trigger."""
from alembic import op
import sqlalchemy as sa

revision = "0041_chat_logos"
down_revision = "0040_child_runs"


def upgrade():
    if "chat_logos" in sa.inspect(op.get_bind()).get_table_names(): return
    op.create_table("chat_logos",
                    sa.Column("trigger_id", sa.Text(), primary_key=True),
                    sa.Column("mime", sa.Text(), nullable=False),
                    sa.Column("data", sa.LargeBinary(), nullable=False),
                    sa.Column("created", sa.Float(), nullable=False))


def downgrade():
    op.drop_table("chat_logos")
