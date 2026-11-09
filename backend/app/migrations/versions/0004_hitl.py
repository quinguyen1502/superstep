"""Human-in-the-loop: runs.owner + runs.checkpoint. Idempotent.

Revision ID: 0004_hitl
Revises: 0003_run_metrics
Create Date: 2026-10-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0004_hitl"
down_revision = "0003_run_metrics"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind()); have = {c["name"] for c in insp.get_columns("runs")}
    with op.batch_alter_table("runs") as b:
        if "owner" not in have: b.add_column(sa.Column("owner", sa.Text))
        if "checkpoint" not in have: b.add_column(sa.Column("checkpoint", sa.Text))
    if "ix_runs_owner" not in {i["name"] for i in sa.inspect(op.get_bind()).get_indexes("runs")}:
        op.create_index("ix_runs_owner", "runs", ["owner"])
    # backfill owners of existing runs from their workflow
    op.execute("UPDATE runs SET owner = (SELECT w.owner FROM workflows w WHERE w.id = runs.workflow_id) WHERE owner IS NULL")


def downgrade() -> None:
    op.drop_index("ix_runs_owner", "runs")
    with op.batch_alter_table("runs") as b:
        b.drop_column("checkpoint"); b.drop_column("owner")
