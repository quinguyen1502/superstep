"""Notifications, webhook deliveries, signing-secret rotation. Idempotent.

Revision ID: 0008_notifications_deliveries
Revises: 0007_hardening
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0008_notifications_deliveries"
down_revision = "0007_hardening"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind()); tables = insp.get_table_names()
    if "notifications" not in tables:
        op.create_table("notifications",
            sa.Column("id", sa.Text, primary_key=True), sa.Column("user_id", sa.Text, nullable=False),
            sa.Column("kind", sa.Text, nullable=False), sa.Column("run_id", sa.Text), sa.Column("workflow_id", sa.Text),
            sa.Column("title", sa.Text, nullable=False), sa.Column("params", sa.Text), sa.Column("link", sa.Text),
            sa.Column("created", sa.Float, nullable=False), sa.Column("read_at", sa.Float))
        op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    if "webhook_deliveries" not in tables:
        op.create_table("webhook_deliveries",
            sa.Column("id", sa.Text, primary_key=True), sa.Column("workflow_id", sa.Text, nullable=False),
            sa.Column("run_id", sa.Text), sa.Column("token_id", sa.Text), sa.Column("url", sa.Text, nullable=False),
            sa.Column("event", sa.Text, nullable=False), sa.Column("payload", sa.Text, nullable=False),
            sa.Column("status", sa.Text, nullable=False), sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
            sa.Column("response_code", sa.Integer), sa.Column("latency_ms", sa.Float), sa.Column("last_error", sa.Text),
            sa.Column("next_attempt", sa.Float), sa.Column("created", sa.Float, nullable=False), sa.Column("updated", sa.Float))
        op.create_index("ix_webhook_deliveries_workflow_id", "webhook_deliveries", ["workflow_id"])
    cols = {c["name"] for c in insp.get_columns("workflow_tokens")}
    with op.batch_alter_table("workflow_tokens") as b:
        if "signing_secret_prev" not in cols: b.add_column(sa.Column("signing_secret_prev", sa.Text))
        if "secret_rotated" not in cols: b.add_column(sa.Column("secret_rotated", sa.Float))


def downgrade() -> None:
    with op.batch_alter_table("workflow_tokens") as b:
        b.drop_column("secret_rotated"); b.drop_column("signing_secret_prev")
    op.drop_table("webhook_deliveries"); op.drop_table("notifications")
