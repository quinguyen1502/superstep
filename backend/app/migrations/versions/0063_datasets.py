"""Add dataset definitions and typed columns."""
import sqlalchemy as sa
from alembic import op

revision = "0063_datasets"
down_revision = "0062_usage_budgets"
branch_labels = depends_on = None


def upgrade():
    op.create_table(
        "datasets",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("owner_id", sa.String(), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("team_id", sa.String(), sa.ForeignKey("teams.id", ondelete="CASCADE")),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("name_key", sa.String(), nullable=False),
        sa.Column("description", sa.String()),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created", sa.Float(), nullable=False),
        sa.Column("updated", sa.Float(), nullable=False),
        sa.CheckConstraint("(owner_id IS NULL) <> (team_id IS NULL)", name="ck_datasets_owner"),
        sa.UniqueConstraint("owner_id", "name_key", name="uq_datasets_owner_name"),
        sa.UniqueConstraint("team_id", "name_key", name="uq_datasets_team_name"),
    )
    op.create_table(
        "dataset_columns",
        sa.Column("dataset_id", sa.String(), sa.ForeignKey("datasets.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("key", sa.String(), primary_key=True),
        sa.Column("label", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False),
        sa.Column("unique", sa.Boolean(), nullable=False),
        sa.Column("default_value", sa.JSON(none_as_null=True)),
        sa.Column("options", sa.JSON(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("archived", sa.Boolean(), nullable=False),
    )


def downgrade():
    op.drop_table("dataset_columns")
    op.drop_table("datasets")
