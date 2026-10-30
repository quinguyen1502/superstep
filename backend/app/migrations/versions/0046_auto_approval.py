"""AI review of approvals (TASK-0186, REQ-0081, DEC-0075): audit columns and the opinion on a waiting step."""
from alembic import op
import sqlalchemy as sa

revision = "0046_auto_approval"
down_revision = "0045_chat_active_agent"

AUDIT = (("auto_outcome", sa.Text()), ("auto_confidence", sa.Float()), ("auto_model", sa.Text()), ("auto_reason", sa.Text()),
         ("auto_rules", sa.Text()), ("policy_hash", sa.Text()), ("agreed", sa.Boolean()))
WAITS = (("ai_decision", sa.Text()), ("ai_confidence", sa.Float()), ("ai_reason", sa.Text()))


def _add(table, cols):
    have = {c["name"] for c in sa.inspect(op.get_bind()).get_columns(table)}
    with op.batch_alter_table(table) as b:
        for name, t in cols:
            if name not in have: b.add_column(sa.Column(name, t, nullable=True))


def upgrade():
    _add("approval_audit", AUDIT)
    _add("approval_waits", WAITS)
    op.create_index("ix_approval_audit_workflow_created", "approval_audit", ["workflow_id", "created"])


def downgrade():
    op.drop_index("ix_approval_audit_workflow_created", "approval_audit")
    with op.batch_alter_table("approval_waits") as b:
        for name, _ in WAITS: b.drop_column(name)
    with op.batch_alter_table("approval_audit") as b:
        for name, _ in AUDIT: b.drop_column(name)
