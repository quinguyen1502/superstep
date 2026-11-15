"""RBAC. users.role (admin | editor | viewer) replaces users.is_admin (admins stay admins), users.active,
and workflow_shares (workflow shared with a user as viewer or editor)."""
from alembic import op
import sqlalchemy as sa

revision = "0021_rbac"
down_revision = "0020_mcp_servers"


def upgrade():
    bind = op.get_bind(); insp = sa.inspect(bind)
    cols = {c["name"] for c in insp.get_columns("users")}
    if "role" not in cols:
        with op.batch_alter_table("users") as b:
            b.add_column(sa.Column("role", sa.Text(), nullable=False, server_default="editor"))
            b.add_column(sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))
        if "is_admin" in cols:
            bind.execute(sa.text("UPDATE users SET role = 'admin' WHERE is_admin = :t"), {"t": True})
            with op.batch_alter_table("users") as b: b.drop_column("is_admin")
    if "workflow_shares" not in insp.get_table_names():
        op.create_table("workflow_shares",
            sa.Column("workflow_id", sa.Text(), sa.ForeignKey("workflows.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("user_id", sa.Text(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True),
            sa.Column("role", sa.Text(), nullable=False), sa.Column("created", sa.Float(), nullable=False),
            sa.Column("shared_by", sa.Text(), nullable=False))


def downgrade():
    op.drop_table("workflow_shares")
    with op.batch_alter_table("users") as b:
        b.add_column(sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.get_bind().execute(sa.text("UPDATE users SET is_admin = :t WHERE role = 'admin'"), {"t": True})
    with op.batch_alter_table("users") as b:
        b.drop_column("active"); b.drop_column("role")
