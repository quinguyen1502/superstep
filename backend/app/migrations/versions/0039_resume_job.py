"""An answer to a waiting run, kept on the run until the resumed segment records something (TASK-0127): an in-memory
job queue loses it on a restart, and start-up recovery queues it again."""
from alembic import op
import sqlalchemy as sa

revision = "0039_resume_job"
down_revision = "0038_workflow_mcp"


def upgrade():
    if "resume_job" not in {c["name"] for c in sa.inspect(op.get_bind()).get_columns("runs")}:
        with op.batch_alter_table("runs") as b: b.add_column(sa.Column("resume_job", sa.Text(), nullable=True))


def downgrade():
    with op.batch_alter_table("runs") as b: b.drop_column("resume_job")
