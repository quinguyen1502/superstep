"""Several Slack workspaces (and Telegram bots) per owner ( follow-up, ). Idempotent.

approval_channels.team_id: the platform account behind the connection, read from the platform when it is saved
(Slack auth.test team_id, Telegram getMe bot id). The shared Slack callback URL routes by it; one connection per
owner, scope and account.

Revision ID: 0013_channel_accounts
Revises: 0012_org_channels
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0013_channel_accounts"
down_revision = "0012_org_channels"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "team_id" not in {c["name"] for c in insp.get_columns("approval_channels")}:
        with op.batch_alter_table("approval_channels") as b: b.add_column(sa.Column("team_id", sa.Text))
    if "ix_approval_channels_team" not in {i["name"] for i in insp.get_indexes("approval_channels")}:
        op.create_index("ix_approval_channels_team", "approval_channels", ["kind", "team_id"])


def downgrade() -> None:
    op.drop_index("ix_approval_channels_team", "approval_channels")
    with op.batch_alter_table("approval_channels") as b: b.drop_column("team_id")
