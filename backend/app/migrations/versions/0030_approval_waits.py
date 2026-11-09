"""waiting steps of runs paused at a Human node and who may answer them (the Approvals inbox, )."""
from alembic import op
import sqlalchemy as sa

revision = "0030_approval_waits"
down_revision = "0029_run_code_runtime"


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "approval_waits" not in tables:
        op.create_table("approval_waits", sa.Column("id", sa.Text(), primary_key=True), sa.Column("run_id", sa.Text(), nullable=False, index=True),
                        sa.Column("node_id", sa.Text(), nullable=False), sa.Column("owner", sa.Text(), nullable=False),
                        sa.Column("workflow_id", sa.Text()), sa.Column("label", sa.Text()), sa.Column("prompt", sa.Text()),
                        sa.Column("channel", sa.Text()), sa.Column("status", sa.Text(), nullable=False), sa.Column("outcome", sa.Text()),
                        sa.Column("created", sa.Float(), nullable=False), sa.Column("closed_at", sa.Float()))
        op.create_index("ix_approval_waits_owner_status", "approval_waits", ["owner", "status"])
    if "approval_wait_approvers" not in tables:
        op.create_table("approval_wait_approvers", sa.Column("wait_id", sa.Text(), primary_key=True),
                        sa.Column("user_id", sa.Text(), primary_key=True, index=True))


def downgrade():
    op.drop_table("approval_wait_approvers"); op.drop_index("ix_approval_waits_owner_status", "approval_waits"); op.drop_table("approval_waits")
