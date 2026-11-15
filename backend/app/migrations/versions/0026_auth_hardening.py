"""sign-in lockout, password reset links, and users.password_changed (older sessions stop working)."""
from alembic import op
import sqlalchemy as sa

revision = "0026_auth_hardening"
down_revision = "0025_kb_dims"


def upgrade():
    insp = sa.inspect(op.get_bind()); tables = set(insp.get_table_names())
    if "password_changed" not in {c["name"] for c in insp.get_columns("users")}:
        op.add_column("users", sa.Column("password_changed", sa.Float(), nullable=True))
    if "login_throttle" not in tables:
        op.create_table("login_throttle", sa.Column("email", sa.Text(), primary_key=True), sa.Column("failures", sa.Integer(), nullable=False),
                        sa.Column("first_at", sa.Float(), nullable=False), sa.Column("locked_until", sa.Float()))
    if "password_resets" not in tables:
        op.create_table("password_resets", sa.Column("id", sa.Text(), primary_key=True), sa.Column("user_id", sa.Text(), nullable=False, index=True),
                        sa.Column("created", sa.Float(), nullable=False), sa.Column("expires", sa.Float(), nullable=False),
                        sa.Column("used", sa.Float()), sa.Column("created_by", sa.Text(), nullable=False))


def downgrade():
    op.drop_table("password_resets"); op.drop_table("login_throttle"); op.drop_column("users", "password_changed")
