"""Record the outcome of Dataset writes in the same transaction as the row."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0066_dataset_receipts"
down_revision = "0065_dataset_access"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "dataset_write_receipts",
        sa.Column("dataset_id", sa.String(), sa.ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("scope", sa.String(128), primary_key=True),
        sa.Column("operation_id", sa.String(128), primary_key=True),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("result", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
        sa.Column("created", sa.Float(), nullable=False),
        sa.UniqueConstraint("scope", "operation_id", name="uq_dataset_write_identity"),
    )


def downgrade():
    op.drop_table("dataset_write_receipts")
