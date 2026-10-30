"""Personal access tokens and CLI device sign-in (TASK-0167, DEC-0071)."""
from alembic import op
import sqlalchemy as sa

revision = "0043_personal_access_tokens"
down_revision = "0042_chat_ratings"


def upgrade():
    bind = op.get_bind()
    names = set(sa.inspect(bind).get_table_names())
    if "personal_access_tokens" not in names:
        op.create_table("personal_access_tokens",
                        sa.Column("id", sa.Text(), primary_key=True),
                        sa.Column("user_id", sa.Text(), nullable=False),
                        sa.Column("name", sa.Text(), nullable=False),
                        sa.Column("token_hash", sa.Text(), nullable=False, unique=True),
                        sa.Column("prefix", sa.Text(), nullable=False),
                        sa.Column("created", sa.Float(), nullable=False),
                        sa.Column("last_used", sa.Float()),
                        sa.Column("revoked", sa.Float()))
        op.create_index("ix_personal_access_tokens_user_id", "personal_access_tokens", ["user_id"])
    if "cli_devices" not in names:
        op.create_table("cli_devices",
                        sa.Column("id", sa.Text(), primary_key=True),
                        sa.Column("device_hash", sa.Text(), nullable=False, unique=True),
                        sa.Column("user_code_hash", sa.Text(), nullable=False, unique=True),
                        sa.Column("name", sa.Text()),
                        sa.Column("user_id", sa.Text()),
                        sa.Column("token_id", sa.Text()),
                        sa.Column("status", sa.Text(), nullable=False),
                        sa.Column("secret", sa.Text()),
                        sa.Column("expires", sa.Float(), nullable=False),
                        sa.Column("created", sa.Float(), nullable=False))


def downgrade():
    op.drop_table("cli_devices")
    op.drop_index("ix_personal_access_tokens_user_id", table_name="personal_access_tokens")
    op.drop_table("personal_access_tokens")
