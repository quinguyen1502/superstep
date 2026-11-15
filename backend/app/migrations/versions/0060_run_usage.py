"""Per-run model usage for the admin Usage page."""
from alembic import op
import sqlalchemy as sa

revision = "0060_run_usage"
down_revision = "0059_usage_indexes"
branch_labels = depends_on = None


def upgrade():
    op.create_table("run_usage", sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("run_id", sa.Text(), nullable=False), sa.Column("workflow_id", sa.Text(), nullable=False),
        sa.Column("owner", sa.Text()), sa.Column("node_id", sa.Text(), nullable=False), sa.Column("kind", sa.Text(), nullable=False),
        sa.Column("model", sa.Text(), nullable=False), sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False, server_default="0"), sa.Column("tokens_out", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("cost_usd", sa.Float()), sa.Column("calls", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("errors", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0"), sa.Column("created", sa.Float(), nullable=False),
        sa.UniqueConstraint("run_id", "node_id", "kind", "model", "provider", name="uq_run_usage_key"))
    op.create_index("ix_run_usage_run_id", "run_usage", ["run_id"])
    op.create_index("ix_run_usage_created", "run_usage", ["created"])
    op.create_index("ix_run_usage_owner_created", "run_usage", ["owner", "created"])


def downgrade():
    op.drop_table("run_usage")
