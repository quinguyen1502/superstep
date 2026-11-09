"""Phase-2 hardening: workflow_tokens.signing_secret (encrypted webhook HMAC secret). Idempotent.

Revision ID: 0007_hardening
Revises: 0006_workflow_versions
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0007_hardening"
down_revision = "0006_workflow_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cols = {c["name"] for c in sa.inspect(op.get_bind()).get_columns("workflow_tokens")}
    if "signing_secret" not in cols:
        with op.batch_alter_table("workflow_tokens") as b: b.add_column(sa.Column("signing_secret", sa.Text))


def downgrade() -> None:
    with op.batch_alter_table("workflow_tokens") as b: b.drop_column("signing_secret")
