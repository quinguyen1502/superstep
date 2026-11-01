"""Chat app keys and external-user session identity (TASK-0217)."""
from alembic import op
import sqlalchemy as sa

revision = "0051_chat_app_keys"
down_revision = "0050_pat_name_unique"


def upgrade():
    op.create_table("chat_app_keys",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("trigger_id", sa.Text(), sa.ForeignKey("workflow_chat_triggers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key_id", sa.Text(), nullable=False, unique=True),
        sa.Column("secret_enc", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("origins", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("created_at", sa.Float(), nullable=False),
        sa.Column("revoked_at", sa.Float()),
        sa.Column("last_used_at", sa.Float()))
    op.create_index("ix_chat_app_keys_trigger_id", "chat_app_keys", ["trigger_id"])
    with op.batch_alter_table("chat_sessions") as b:
        b.add_column(sa.Column("external_user", sa.Text()))
        b.add_column(sa.Column("app_key_id", sa.Text()))
        b.create_index("ix_chat_sessions_trigger_external_user", ["trigger_id", "external_user"])


def downgrade():
    with op.batch_alter_table("chat_sessions") as b:
        b.drop_index("ix_chat_sessions_trigger_external_user")
        b.drop_column("app_key_id")
        b.drop_column("external_user")
    op.drop_table("chat_app_keys")
