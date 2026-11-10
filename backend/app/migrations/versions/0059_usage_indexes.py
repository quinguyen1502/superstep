"""Indexes for the admin usage page, product health counts and readiness."""
from alembic import op

revision = '0059_usage_indexes'
down_revision = '0058_browser_approvals'
branch_labels = depends_on = None

INDEXES = [
    ('ix_runs_started', 'runs', ['started']),                                     # usage window
    ('ix_runs_status_started', 'runs', ['status', 'started']),                    # oldest queued run
    ('ix_approval_waits_status_created', 'approval_waits', ['status', 'created']),  # waiting approvals
    ('ix_webhook_deliveries_status_updated', 'webhook_deliveries', ['status', 'updated']),  # failed deliveries
]


def upgrade():
    for name, table, cols in INDEXES: op.create_index(name, table, cols)


def downgrade():
    for name, table, _ in reversed(INDEXES): op.drop_index(name, table_name=table)
