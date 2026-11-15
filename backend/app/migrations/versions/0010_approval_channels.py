"""Approval through external channels: channels, identities, requests, audit. Idempotent.

Revision ID: 0010_approval_channels
Revises: 0009_effectively_once
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_approval_channels"
down_revision = "0009_effectively_once"
branch_labels = None
depends_on = None

T, F = sa.Text, sa.Float


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "approval_channels" not in tables:
        op.create_table("approval_channels", sa.Column("id", T, primary_key=True), sa.Column("owner", T, nullable=False),
                        sa.Column("kind", T, nullable=False), sa.Column("secrets", T, nullable=False), sa.Column("hint", T),
                        sa.Column("created", F, nullable=False), sa.UniqueConstraint("owner", "kind", name="uq_approval_channels_owner_kind"))
        op.create_index("ix_approval_channels_owner", "approval_channels", ["owner"])
    if "channel_identities" not in tables:
        op.create_table("channel_identities", sa.Column("user_id", T, primary_key=True), sa.Column("kind", T, primary_key=True),
                        sa.Column("external_id", T, nullable=False), sa.Column("created", F, nullable=False),
                        sa.UniqueConstraint("kind", "external_id", name="uq_channel_identities_kind_external"))
    if "approval_requests" not in tables:
        op.create_table("approval_requests", sa.Column("id", T, primary_key=True), sa.Column("run_id", T, nullable=False),
                        sa.Column("node_id", T, nullable=False), sa.Column("owner", T, nullable=False), sa.Column("workflow_id", T),
                        sa.Column("channel_id", T, nullable=False), sa.Column("kind", T, nullable=False), sa.Column("target", T, nullable=False),
                        sa.Column("approvers", T, nullable=False), sa.Column("nonce", T, nullable=False), sa.Column("expires", F, nullable=False),
                        sa.Column("message_ref", T), sa.Column("status", T, nullable=False), sa.Column("decided_by", T),
                        sa.Column("decided_external", T), sa.Column("decided_at", F), sa.Column("created", F, nullable=False))
        op.create_index("ix_approval_requests_run_id", "approval_requests", ["run_id"])
        op.create_index("ix_approval_requests_owner", "approval_requests", ["owner"])
    if "approval_audit" not in tables:
        op.create_table("approval_audit", sa.Column("id", T, primary_key=True), sa.Column("owner", T, nullable=False),
                        sa.Column("request_id", T), sa.Column("run_id", T), sa.Column("workflow_id", T), sa.Column("kind", T, nullable=False),
                        sa.Column("action", T, nullable=False), sa.Column("code", T), sa.Column("actor_id", T), sa.Column("external_id", T),
                        sa.Column("created", F, nullable=False))
        op.create_index("ix_approval_audit_owner", "approval_audit", ["owner"])
        op.create_index("ix_approval_audit_created", "approval_audit", ["created"])


def downgrade() -> None:
    for t in ("approval_audit", "approval_requests", "channel_identities", "approval_channels"): op.drop_table(t)
