"""Monthly usage budgets and deduplicated warning claims."""
import sqlalchemy as sa
from alembic import op

revision = "0062_usage_budgets"
down_revision = "0061_chat_refusals"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "usage_budgets",
        sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("user_id", sa.Text(), sa.ForeignKey("users.id", ondelete="CASCADE"), unique=True),
        sa.Column("team_id", sa.Text(), sa.ForeignKey("teams.id", ondelete="CASCADE"), unique=True),
        sa.Column("amount_cents", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Text(), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("created", sa.Float(), nullable=False),
        sa.CheckConstraint("(user_id IS NULL) <> (team_id IS NULL)", name="ck_usage_budget_target"),
        sa.CheckConstraint("amount_cents > 0", name="ck_usage_budget_positive"),
    )
    op.create_table(
        "usage_budget_warnings",
        sa.Column("budget_id", sa.Text(), sa.ForeignKey("usage_budgets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("month", sa.Text(), primary_key=True),
        sa.Column("threshold", sa.Integer(), primary_key=True),
    )


def downgrade():
    op.drop_table("usage_budget_warnings")
    op.drop_table("usage_budgets")
