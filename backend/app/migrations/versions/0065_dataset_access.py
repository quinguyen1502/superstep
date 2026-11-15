"""Add explicit workflow grants and scoped Dataset API credentials."""
import sqlalchemy as sa
from alembic import op

revision = "0065_dataset_access"
down_revision = "0064_dataset_rows"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "dataset_workflow_grants",
        sa.Column("dataset_id", sa.String(), sa.ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("workflow_id", sa.String(), sa.ForeignKey("workflows.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("permission", sa.String(), nullable=False),
        sa.Column("created", sa.Float(), nullable=False),
        sa.CheckConstraint("permission in ('read', 'write', 'read_write')", name="ck_dataset_grants_permission"),
    )
    op.create_index("ix_dataset_grants_workflow", "dataset_workflow_grants", ["workflow_id"])
    op.create_table(
        "dataset_api_tokens",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("dataset_id", sa.String(), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("issuer_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("permission", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("prefix", sa.String(), nullable=False),
        sa.Column("created", sa.Float(), nullable=False),
        sa.Column("revoked", sa.Float()),
        sa.CheckConstraint("permission in ('read', 'write', 'read_write')", name="ck_dataset_tokens_permission"),
    )
    op.create_index("ix_dataset_tokens_dataset", "dataset_api_tokens", ["dataset_id"])


def downgrade():
    op.drop_table("dataset_api_tokens")
    op.drop_table("dataset_workflow_grants")
