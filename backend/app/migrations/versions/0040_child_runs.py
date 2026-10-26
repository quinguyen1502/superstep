"""Child runs of workflow tools (TASK-0134, DEC-0066): the parent run and the Agent tool call that started each one.
One child per call: (parent_run_id, parent_step) is unique."""
from alembic import op
import sqlalchemy as sa

revision = "0040_child_runs"
down_revision = "0039_resume_job"


def upgrade():
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("runs")}
    with op.batch_alter_table("runs") as b:
        if "parent_run_id" not in cols: b.add_column(sa.Column("parent_run_id", sa.Text(), nullable=True))
        if "parent_step" not in cols: b.add_column(sa.Column("parent_step", sa.Text(), nullable=True))
    op.create_index("ix_runs_parent_run_id", "runs", ["parent_run_id"])
    op.create_index("ux_runs_parent_call", "runs", ["parent_run_id", "parent_step"], unique=True)


def downgrade():
    op.drop_index("ux_runs_parent_call", table_name="runs")
    op.drop_index("ix_runs_parent_run_id", table_name="runs")
    with op.batch_alter_table("runs") as b:
        b.drop_column("parent_step"); b.drop_column("parent_run_id")
