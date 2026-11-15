"""Per-run summary metrics + trace id. Idempotent like 0001/0002.

Revision ID: 0003_run_metrics
Revises: 0002_credentials
Create Date: 2026-10-16
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_run_metrics"
down_revision = "0002_credentials"
branch_labels = None
depends_on = None

COLUMNS = [("duration_ms", sa.Float), ("tokens_in", sa.Integer), ("tokens_out", sa.Integer),
           ("cost_usd", sa.Float), ("error_count", sa.Integer), ("trace_id", sa.Text)]


def upgrade() -> None:
    have = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("runs")}
    with op.batch_alter_table("runs") as b:
        for name, typ in COLUMNS:
            if name not in have: b.add_column(sa.Column(name, typ))


def downgrade() -> None:
    with op.batch_alter_table("runs") as b:
        for name, _ in reversed(COLUMNS): b.drop_column(name)
