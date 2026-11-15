"""Org-wide approval channels managed by admins ( follow-up, ). Idempotent; SQLite batch + Postgres.

- users.is_admin: who may create / edit / delete org-wide channels (set from STUDIO_ADMIN_EMAILS and the demo user).
- approval_channels.scope (user | org) and an optional display name; the one-per-(owner, kind) unique constraint
  goes away (an admin can own a personal and an org connection; the service keeps one per owner/scope/kind).

Revision ID: 0012_org_channels
Revises: 0011_identity_verification
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0012_org_channels"
down_revision = "0011_identity_verification"
branch_labels = None
depends_on = None


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    ucols = {c["name"] for c in insp.get_columns("users")}
    if "is_admin" not in ucols:
        with op.batch_alter_table("users") as b: b.add_column(sa.Column("is_admin", sa.Boolean, nullable=False, server_default=sa.false()))
    ccols = {c["name"] for c in insp.get_columns("approval_channels")}
    uqs = {u["name"] for u in insp.get_unique_constraints("approval_channels")}
    with op.batch_alter_table("approval_channels") as b:
        if "scope" not in ccols: b.add_column(sa.Column("scope", sa.Text, nullable=False, server_default="user"))
        if "name" not in ccols: b.add_column(sa.Column("name", sa.Text))
        if "uq_approval_channels_owner_kind" in uqs: b.drop_constraint("uq_approval_channels_owner_kind", type_="unique")
    if "ix_approval_channels_scope" not in {i["name"] for i in insp.get_indexes("approval_channels")}:
        op.create_index("ix_approval_channels_scope", "approval_channels", ["scope"])


def downgrade() -> None:
    op.drop_index("ix_approval_channels_scope", "approval_channels")
    with op.batch_alter_table("approval_channels") as b:
        b.drop_column("name"); b.drop_column("scope")
    with op.batch_alter_table("users") as b: b.drop_column("is_admin")
