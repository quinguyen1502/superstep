"""users.lang: the language of chat messages sent for the user ( follow-up). Idempotent.

Set by the studio's language switcher through the notification preferences; NULL means English.

Revision ID: 0014_user_lang
Revises: 0013_channel_accounts
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0014_user_lang"
down_revision = "0013_channel_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if "lang" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("users")}:
        with op.batch_alter_table("users") as b: b.add_column(sa.Column("lang", sa.Text))


def downgrade() -> None:
    with op.batch_alter_table("users") as b: b.drop_column("lang")
