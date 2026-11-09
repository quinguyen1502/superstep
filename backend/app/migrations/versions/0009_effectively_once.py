"""Effectively-once execution + notification preferences. Idempotent.

- runs.lease_gen: fencing token, bumped each time a worker claims the run; writes carry it.
- node_results: ledger of finished side-effect nodes (run, node, iteration) reused on recovery.
- users.notify_in_app / users.notify_email: per-user notification preferences.

Revision ID: 0009_effectively_once
Revises: 0008_notifications_deliveries
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0009_effectively_once"
down_revision = "0008_notifications_deliveries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind()); tables = insp.get_table_names()
    if "node_results" not in tables:
        op.create_table("node_results",
            sa.Column("run_id", sa.Text, primary_key=True), sa.Column("node_id", sa.Text, primary_key=True),
            sa.Column("iteration", sa.Integer, primary_key=True), sa.Column("delta", sa.Text, nullable=False),
            sa.Column("idempotency_key", sa.Text, nullable=False), sa.Column("created", sa.Float, nullable=False))
    run_cols = {c["name"] for c in insp.get_columns("runs")}
    if "lease_gen" not in run_cols:
        with op.batch_alter_table("runs") as b: b.add_column(sa.Column("lease_gen", sa.Integer, nullable=False, server_default="0"))
    user_cols = {c["name"] for c in insp.get_columns("users")}
    with op.batch_alter_table("users") as b:
        if "notify_in_app" not in user_cols: b.add_column(sa.Column("notify_in_app", sa.Boolean, nullable=False, server_default=sa.true()))
        if "notify_email" not in user_cols: b.add_column(sa.Column("notify_email", sa.Boolean, nullable=False, server_default=sa.true()))


def downgrade() -> None:
    with op.batch_alter_table("users") as b:
        b.drop_column("notify_email"); b.drop_column("notify_in_app")
    with op.batch_alter_table("runs") as b: b.drop_column("lease_gen")
    op.drop_table("node_results")
