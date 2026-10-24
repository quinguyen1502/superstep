"""LangSmith: the root span of a run's trace (its LangSmith run id) and the experiment a test suite was sent to."""
from alembic import op
import sqlalchemy as sa

revision = "0037_langsmith"
down_revision = "0036_agent_threads"


def upgrade():
    insp = sa.inspect(op.get_bind())
    if "trace_root" not in {c["name"] for c in insp.get_columns("runs")}:
        with op.batch_alter_table("runs") as b: b.add_column(sa.Column("trace_root", sa.Text()))
    if "langsmith_url" not in {c["name"] for c in insp.get_columns("workflow_test_suites")}:
        with op.batch_alter_table("workflow_test_suites") as b: b.add_column(sa.Column("langsmith_url", sa.Text()))


def downgrade():
    with op.batch_alter_table("workflow_test_suites") as b: b.drop_column("langsmith_url")
    with op.batch_alter_table("runs") as b: b.drop_column("trace_root")
