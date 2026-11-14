"""Store Dataset column rules and display preferences."""
from alembic import op
import sqlalchemy as sa

revision = "0071_dataset_column_rules"
down_revision = "0070_dataset_auto_number"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("dataset_columns", sa.Column("validation_rules", sa.JSON(), nullable=True))
    op.add_column("dataset_columns", sa.Column("display_format", sa.JSON(), nullable=True))


def downgrade():
    op.drop_column("dataset_columns", "display_format")
    op.drop_column("dataset_columns", "validation_rules")
