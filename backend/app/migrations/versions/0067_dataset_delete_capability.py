"""Add a delete capability beside Dataset grant and token permissions."""
import sqlalchemy as sa
from alembic import op

revision = "0067_dataset_delete_capability"
down_revision = "0066_dataset_receipts"
branch_labels = depends_on = None


def upgrade():
    for table in ("dataset_workflow_grants", "dataset_api_tokens"):
        op.add_column(table, sa.Column("allow_delete", sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    for table in ("dataset_api_tokens", "dataset_workflow_grants"):
        op.drop_column(table, "allow_delete")
