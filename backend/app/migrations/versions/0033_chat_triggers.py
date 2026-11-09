"""chat triggers and the granted Slack scopes of a connection."""
from alembic import op
import sqlalchemy as sa

revision = "0033_chat_triggers"
down_revision = "0032_workflow_tests"


def upgrade():
    insp = sa.inspect(op.get_bind())
    if "workflow_chat_triggers" not in set(insp.get_table_names()):
        op.create_table("workflow_chat_triggers", sa.Column("id", sa.Text(), primary_key=True), sa.Column("workflow_id", sa.Text(), index=True),
                        sa.Column("owner", sa.Text(), nullable=False), sa.Column("name", sa.Text(), nullable=False),
                        sa.Column("channel_id", sa.Text(), index=True), sa.Column("place", sa.Text(), nullable=False),
                        sa.Column("command", sa.Text(), nullable=False), sa.Column("input_field", sa.Text(), nullable=False),
                        sa.Column("reply_field", sa.Text(), nullable=False), sa.Column("enabled", sa.Boolean(), server_default=sa.true()),
                        sa.Column("note", sa.Text()), sa.Column("last_message", sa.Float()), sa.Column("last_run_id", sa.Text()),
                        sa.Column("created", sa.Float(), nullable=False))
        op.create_index("uq_workflow_chat_triggers_command", "workflow_chat_triggers", ["channel_id", "place", "command"], unique=True)
    if "scopes" not in {c["name"] for c in insp.get_columns("approval_channels")}:
        op.add_column("approval_channels", sa.Column("scopes", sa.Text()))


def downgrade():
    op.drop_column("approval_channels", "scopes")
    op.drop_index("uq_workflow_chat_triggers_command", "workflow_chat_triggers"); op.drop_table("workflow_chat_triggers")
