"""Add persistent Dataset rows and unique field keys."""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0064_dataset_rows"
down_revision = "0063_datasets"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "dataset_rows",
        sa.Column("dataset_id", sa.String(), sa.ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("values", sa.JSON().with_variant(JSONB(), "postgresql"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created", sa.Float(), nullable=False),
        sa.Column("updated", sa.Float(), nullable=False),
    )
    op.create_index("ix_dataset_rows_created", "dataset_rows", ["dataset_id", "created", "id"])
    op.create_table(
        "dataset_row_keys",
        sa.Column("dataset_id", sa.String(), primary_key=True),
        sa.Column("field", sa.String(), primary_key=True),
        sa.Column("value_hash", sa.String(), primary_key=True),
        sa.Column("row_id", sa.String(), nullable=False),
        sa.ForeignKeyConstraint(["dataset_id", "row_id"], ["dataset_rows.dataset_id", "dataset_rows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["dataset_id", "field"], ["dataset_columns.dataset_id", "dataset_columns.key"], ondelete="CASCADE"),
    )
    op.create_index("ix_dataset_row_keys_row", "dataset_row_keys", ["dataset_id", "row_id"])


def downgrade():
    op.drop_table("dataset_row_keys")
    op.drop_table("dataset_rows")
