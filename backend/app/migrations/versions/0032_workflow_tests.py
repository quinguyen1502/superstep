"""workflow test cases, suite runs and their results."""
from alembic import op
import sqlalchemy as sa

revision = "0032_workflow_tests"
down_revision = "0031_approval_deadlines"


def upgrade():
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "workflow_tests" not in tables:
        op.create_table("workflow_tests", sa.Column("id", sa.Text(), primary_key=True), sa.Column("workflow_id", sa.Text(), index=True),
                        sa.Column("name", sa.Text(), nullable=False), sa.Column("input", sa.Text(), nullable=False),
                        sa.Column("answers", sa.Text(), nullable=False), sa.Column("checks", sa.Text(), nullable=False),
                        sa.Column("position", sa.Integer()), sa.Column("author", sa.Text()),
                        sa.Column("created", sa.Float(), nullable=False), sa.Column("updated", sa.Float(), nullable=False))
    if "workflow_test_suites" not in tables:
        op.create_table("workflow_test_suites", sa.Column("id", sa.Text(), primary_key=True), sa.Column("workflow_id", sa.Text(), index=True),
                        sa.Column("version", sa.Integer()), sa.Column("owner", sa.Text(), nullable=False), sa.Column("status", sa.Text(), nullable=False),
                        sa.Column("mock", sa.Boolean(), server_default=sa.false()), sa.Column("total", sa.Integer()),
                        sa.Column("passed", sa.Integer()), sa.Column("failed", sa.Integer()),
                        sa.Column("started", sa.Float(), nullable=False), sa.Column("ended", sa.Float()))
        op.create_index("uq_workflow_test_suites_running", "workflow_test_suites", ["workflow_id"], unique=True,
                        sqlite_where=sa.text("status = 'running'"), postgresql_where=sa.text("status = 'running'"))
    if "workflow_test_results" not in tables:
        op.create_table("workflow_test_results", sa.Column("id", sa.Text(), primary_key=True), sa.Column("suite_id", sa.Text(), index=True),
                        sa.Column("test_id", sa.Text()), sa.Column("name", sa.Text(), nullable=False), sa.Column("case", sa.Text(), nullable=False),
                        sa.Column("position", sa.Integer()), sa.Column("status", sa.Text(), nullable=False),
                        sa.Column("run_id", sa.Text(), index=True), sa.Column("version", sa.Integer()), sa.Column("checks", sa.Text()),
                        sa.Column("reason", sa.Text()), sa.Column("detail", sa.Text()), sa.Column("ended", sa.Float()))


def downgrade():
    op.drop_table("workflow_test_results")
    op.drop_index("uq_workflow_test_suites_running", "workflow_test_suites"); op.drop_table("workflow_test_suites")
    op.drop_table("workflow_tests")
