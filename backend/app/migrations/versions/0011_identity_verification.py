"""Verified channel identities ( follow-up, ). Idempotent; works on SQLite (batch) and Postgres.

- channel_identities: verified_at + one-time code state (hash, expiry, last send, failed attempts).
- The (kind, external_id) unique constraint goes away: an unverified link must not block the real owner of the
  account; uniqueness among *verified* links is enforced when a code is confirmed. Existing links stay unverified
  on purpose (they were never proven), so their owners verify once.

Revision ID: 0011_identity_verification
Revises: 0010_approval_channels
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_identity_verification"
down_revision = "0010_approval_channels"
branch_labels = None
depends_on = None

NEW = (("verified_at", sa.Float), ("code_hash", sa.Text), ("code_expires", sa.Float), ("code_sent_at", sa.Float))


def upgrade() -> None:
    insp = sa.inspect(op.get_bind())
    cols = {c["name"] for c in insp.get_columns("channel_identities")}
    uqs = {u["name"] for u in insp.get_unique_constraints("channel_identities")}
    idx = {i["name"] for i in insp.get_indexes("channel_identities")}
    with op.batch_alter_table("channel_identities") as b:
        for name, typ in NEW:
            if name not in cols: b.add_column(sa.Column(name, typ))
        if "code_attempts" not in cols: b.add_column(sa.Column("code_attempts", sa.Integer, nullable=False, server_default="0"))
        if "uq_channel_identities_kind_external" in uqs: b.drop_constraint("uq_channel_identities_kind_external", type_="unique")
    if "ix_channel_identities_external" not in idx:
        op.create_index("ix_channel_identities_external", "channel_identities", ["kind", "external_id"])


def downgrade() -> None:
    op.drop_index("ix_channel_identities_external", "channel_identities")
    with op.batch_alter_table("channel_identities") as b:
        for name, _ in NEW: b.drop_column(name)
        b.drop_column("code_attempts")
        b.create_unique_constraint("uq_channel_identities_kind_external", ["kind", "external_id"])
