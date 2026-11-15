"""Human node deadlines on waiting steps (due time, reminders, escalation)."""
from alembic import op
import sqlalchemy as sa

revision = "0031_approval_deadlines"
down_revision = "0030_approval_waits"
COLUMNS = (("approval", sa.Text()), ("deadline", sa.Text()), ("due_at", sa.Float()), ("next_remind_at", sa.Float()),
           ("reminders", sa.Integer()), ("escalated_at", sa.Float()))


def upgrade():
    have = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("approval_waits")}
    with op.batch_alter_table("approval_waits") as b:
        for name, kind in COLUMNS:
            if name in have: continue
            b.add_column(sa.Column(name, kind, nullable=name != "reminders", **({"server_default": "0"} if name == "reminders" else {})))
            if name in ("due_at", "next_remind_at"): b.create_index(f"ix_approval_waits_{name}", [name])


def downgrade():
    with op.batch_alter_table("approval_waits") as b:
        b.drop_index("ix_approval_waits_next_remind_at"); b.drop_index("ix_approval_waits_due_at")
        for name, _ in reversed(COLUMNS): b.drop_column(name)
