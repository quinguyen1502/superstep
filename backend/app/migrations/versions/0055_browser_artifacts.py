"""Private browser screenshots with bounded retention."""
from alembic import op
import sqlalchemy as sa

revision = "0055_browser_artifacts"
down_revision = "0054_chat_regenerate"
branch_labels = depends_on = None


def upgrade():
    op.create_table("browser_artifacts", sa.Column("id", sa.Text(), primary_key=True),
        sa.Column("owner", sa.Text(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("principal_id", sa.Text(), nullable=False), sa.Column("run_id", sa.Text(), nullable=False),
        sa.Column("connection_id", sa.Text(), nullable=False), sa.Column("group_id", sa.Text(), nullable=False),
        sa.Column("created", sa.Float(), nullable=False), sa.Column("expires", sa.Float(), nullable=False),
        sa.Column("data", sa.LargeBinary(), nullable=False))
    for column in ("owner", "run_id", "expires"):
        op.create_index(f"ix_browser_artifacts_{column}", "browser_artifacts", [column])


def downgrade():
    op.drop_table("browser_artifacts")
