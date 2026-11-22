"""Persist the Dataset revision used to resync live readers."""

import sqlalchemy as sa
from alembic import op

revision = "0073_dataset_data_revision"
down_revision = "0072_dataset_formulas"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("datasets", sa.Column("data_revision", sa.BigInteger(), nullable=False, server_default="1"))


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # Start a transaction before the DDL in SQLite's legacy transaction mode.
        # A guard in a following downgrade can then roll back this column drop.
        datasets = sa.table("datasets", sa.column("data_revision"))
        bind.execute(datasets.update().where(sa.false()).values(data_revision=datasets.c.data_revision))
    op.drop_column("datasets", "data_revision")
