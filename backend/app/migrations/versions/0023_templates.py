"""workflow templates (personal and org-wide; built-ins are defined in code)."""
from alembic import op
import sqlalchemy as sa

revision = "0023_templates"
down_revision = "0022_teams_audit"


def upgrade():
    if "workflow_templates" in set(sa.inspect(op.get_bind()).get_table_names()): return
    op.create_table("workflow_templates", sa.Column("id", sa.Text(), primary_key=True), sa.Column("name", sa.Text(), nullable=False),
                    sa.Column("description", sa.Text()), sa.Column("scope", sa.Text(), nullable=False),
                    sa.Column("owner", sa.Text(), nullable=False, index=True), sa.Column("data", sa.Text(), nullable=False),
                    sa.Column("created", sa.Float(), nullable=False), sa.Column("updated", sa.Float(), nullable=False))


def downgrade():
    op.drop_table("workflow_templates")
