"""AI review safety (TASK-0204): a waiting step remembers that its AI review is still due, so a review lost to a restart
is noticed, and a per-workflow, per-day counter reserves the daily cap atomically."""
from alembic import op
import sqlalchemy as sa

revision = "0049_review_recovery"
down_revision = "0048_attachment_location"


def upgrade():
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("approval_waits")}
    if "review" not in cols:
        with op.batch_alter_table("approval_waits") as b: b.add_column(sa.Column("review", sa.Text(), nullable=True))
    if "approval_auto_quota" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table("approval_auto_quota", sa.Column("workflow_id", sa.Text(), primary_key=True),
                        sa.Column("day", sa.Float(), primary_key=True), sa.Column("used", sa.Integer(), nullable=False, server_default="0"))


def downgrade():
    op.drop_table("approval_auto_quota")
    with op.batch_alter_table("approval_waits") as b: b.drop_column("review")
