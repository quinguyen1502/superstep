"""runs.callback_url / runs.callback_token_id ( follow-up). Idempotent.

An API-triggered run keeps its result callback, so a run resumed later (from Slack / Telegram, by a worker job that
no longer has the original start job) still sends its callback_url webhook through the delivery pipeline.

Revision ID: 0015_run_callbacks
Revises: 0014_user_lang
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0015_run_callbacks"
down_revision = "0014_user_lang"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("runs")}
    with op.batch_alter_table("runs") as b:
        if "callback_url" not in cols: b.add_column(sa.Column("callback_url", sa.Text))
        if "callback_token_id" not in cols: b.add_column(sa.Column("callback_token_id", sa.Text))


def downgrade() -> None:
    with op.batch_alter_table("runs") as b:
        b.drop_column("callback_token_id"); b.drop_column("callback_url")
