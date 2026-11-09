"""Workflow versions + runs.workflow_version. Idempotent; existing workflows become v1.

Revision ID: 0006_workflow_versions
Revises: 0005_api_triggers
Create Date: 2026-10-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_workflow_versions"
down_revision = "0005_api_triggers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    if "workflow_versions" not in insp.get_table_names():
        op.create_table("workflow_versions",
            sa.Column("id", sa.Text, primary_key=True), sa.Column("workflow_id", sa.Text, nullable=False),
            sa.Column("version", sa.Integer, nullable=False), sa.Column("name", sa.Text), sa.Column("data", sa.Text, nullable=False),
            sa.Column("author", sa.Text), sa.Column("created", sa.Float), sa.Column("note", sa.Text),
            sa.UniqueConstraint("workflow_id", "version", name="uq_workflow_versions_wf_version"))
        op.create_index("ix_workflow_versions_workflow_id", "workflow_versions", ["workflow_id"])
        # every existing workflow starts with its current content as v1 (portable SQL: SQLite + Postgres)
        op.execute("INSERT INTO workflow_versions (id, workflow_id, version, name, data, author, created, note) "
                   "SELECT id || '-v1', id, 1, name, COALESCE(data, '{}'), owner, updated, 'Initial version' FROM workflows")
    if "workflow_version" not in {c["name"] for c in insp.get_columns("runs")}:
        with op.batch_alter_table("runs") as b: b.add_column(sa.Column("workflow_version", sa.Integer))


def downgrade() -> None:
    with op.batch_alter_table("runs") as b: b.drop_column("workflow_version")
    op.drop_table("workflow_versions")
