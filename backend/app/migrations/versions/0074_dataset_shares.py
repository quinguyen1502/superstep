"""Store the fixed projection and hashed capability of each Dataset share."""

import sqlalchemy as sa
from alembic import op

revision = "0074_dataset_shares"
down_revision = "0073_dataset_data_revision"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "dataset_shares",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("dataset_id", sa.String(), sa.ForeignKey("datasets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column("filter_tree", sa.JSON(none_as_null=True)),
        sa.Column("schema_signature", sa.JSON(), nullable=False),
        sa.Column("token_hash", sa.String(64), unique=True, nullable=False),
        sa.Column("created", sa.Float(), nullable=False),
        sa.Column("updated", sa.Float(), nullable=False),
        sa.Column("revoked", sa.Float()),
    )
    op.create_index("ix_dataset_shares_dataset", "dataset_shares", ["dataset_id", "revoked", "created"])


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        # Keep the drop transactional if an older downgrade guard rejects the migration.
        bind.execute(sa.delete(sa.table("dataset_shares")).where(sa.false()))
    op.drop_table("dataset_shares")
