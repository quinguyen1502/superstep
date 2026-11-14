"""Persist the dataset auto-number watermark.

Revision ID: 0070_dataset_auto_number
Revises: 0069_dataset_receipt_retention
"""
from alembic import op
import sqlalchemy as sa

revision = "0070_dataset_auto_number"
down_revision = "0069_dataset_receipt_retention"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("datasets", sa.Column("auto_number_counter", sa.BigInteger(), nullable=False, server_default="0"))


def downgrade():
    op.drop_column("datasets", "auto_number_counter")
