"""Add optional Relation definitions and indexed row edges."""

import sqlalchemy as sa
from alembic import op

revision = "0075_dataset_relations"
down_revision = "0074_dataset_shares"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("dataset_columns", sa.Column("relation_target_id", sa.String()))
    op.add_column("dataset_columns", sa.Column("relation_display_key", sa.String()))
    op.create_index("ix_dataset_columns_relation_target", "dataset_columns", ["relation_target_id", "relation_display_key"])
    op.create_table(
        "dataset_relation_edges",
        sa.Column("source_dataset_id", sa.String(), primary_key=True),
        sa.Column("source_row_id", sa.String(), primary_key=True),
        sa.Column("field", sa.String(), primary_key=True),
        sa.Column("target_dataset_id", sa.String(), nullable=False),
        sa.Column("target_row_id", sa.String(), nullable=False),
        sa.CheckConstraint("source_dataset_id <> target_dataset_id", name="ck_dataset_relation_distinct"),
        sa.ForeignKeyConstraint(("source_dataset_id", "field"), ("dataset_columns.dataset_id", "dataset_columns.key"),
                                name="fk_dataset_relation_source_field", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(("source_dataset_id", "source_row_id"), ("dataset_rows.dataset_id", "dataset_rows.id"),
                                name="fk_dataset_relation_source_row", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(("target_dataset_id", "target_row_id"), ("dataset_rows.dataset_id", "dataset_rows.id"),
                                name="fk_dataset_relation_target_row", ondelete="RESTRICT"),
    )
    op.create_index("ix_dataset_relation_target", "dataset_relation_edges", ["target_dataset_id", "target_row_id"])
    op.create_index("ix_dataset_relation_source_field", "dataset_relation_edges", ["source_dataset_id", "field"])


def downgrade():
    columns = sa.table("dataset_columns", sa.column("relation_target_id"), sa.column("archived", sa.Boolean()))
    edges = sa.table("dataset_relation_edges")
    bind = op.get_bind()
    active = sa.select(sa.literal(1)).where(columns.c.relation_target_id.is_not(None), columns.c.archived.is_(False)).limit(1)
    if bind.scalar(active) or bind.scalar(sa.select(sa.literal(1)).select_from(edges).limit(1)):
        raise RuntimeError("Remove active Dataset Relation columns or restore a pre-Relation backup before downgrading.")
    if bind.dialect.name == "sqlite":
        bind.execute(sa.delete(edges).where(sa.false()))
    op.drop_table("dataset_relation_edges")
    op.drop_index("ix_dataset_columns_relation_target", table_name="dataset_columns")
    op.drop_column("dataset_columns", "relation_display_key")
    op.drop_column("dataset_columns", "relation_target_id")
