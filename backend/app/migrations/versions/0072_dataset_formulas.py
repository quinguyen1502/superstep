"""Add optional Dataset formula definitions and row diagnostics."""

from alembic import op
import sqlalchemy as sa

revision = "0072_dataset_formulas"
down_revision = "0071_dataset_column_rules"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("dataset_columns", sa.Column("formula", sa.JSON(), nullable=True))
    op.add_column("dataset_rows", sa.Column("formula_errors", sa.JSON(), nullable=True))


def downgrade():
    columns = sa.table("dataset_columns", sa.column("formula"), sa.column("archived", sa.Boolean()))
    active = sa.select(sa.literal(1)).where(columns.c.formula.is_not(None), columns.c.archived.is_(False)).limit(1)
    if op.get_bind().scalar(active) is not None:
        raise RuntimeError("Remove active Dataset Formula columns or restore a pre-Formula backup before downgrading.")
    op.drop_column("dataset_rows", "formula_errors")
    op.drop_column("dataset_columns", "formula")
