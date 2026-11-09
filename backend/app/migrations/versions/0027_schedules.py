"""cron schedules that start workflow runs."""
from alembic import op
import sqlalchemy as sa

revision = "0027_schedules"
down_revision = "0026_auth_hardening"


def upgrade():
    if "workflow_schedules" in set(sa.inspect(op.get_bind()).get_table_names()): return
    op.create_table("workflow_schedules", sa.Column("id", sa.Text(), primary_key=True), sa.Column("workflow_id", sa.Text(), index=True),
                    sa.Column("owner", sa.Text(), nullable=False), sa.Column("name", sa.Text(), nullable=False),
                    sa.Column("cron", sa.Text(), nullable=False), sa.Column("timezone", sa.Text(), nullable=False),
                    sa.Column("input", sa.Text(), nullable=False), sa.Column("enabled", sa.Boolean(), server_default=sa.true(), nullable=False),
                    sa.Column("next_run", sa.Float(), index=True), sa.Column("last_run", sa.Float()), sa.Column("last_run_id", sa.Text()),
                    sa.Column("note", sa.Text()), sa.Column("created", sa.Float(), nullable=False))


def downgrade():
    op.drop_table("workflow_schedules")
