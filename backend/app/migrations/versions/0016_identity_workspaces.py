"""Chat identities per workspace ( follow-up, ). Idempotent; SQLite (batch) and Postgres.

channel_identities gets team_id ("" for platforms without workspaces, e.g. Telegram) and the primary key becomes
(user_id, kind, team_id): one account per user, platform and Slack workspace. Backfill: a Slack link gets the
workspace of the connection its verification code was sent through (the user's oldest personal Slack connection,
else the oldest org one, i.e. what dm_channel chose); without any connection it stays "" (shown, not usable).

Revision ID: 0016_identity_workspaces
Revises: 0015_run_callbacks
Create Date: 2026-10-17
"""
from alembic import op
import sqlalchemy as sa

revision = "0016_identity_workspaces"
down_revision = "0015_run_callbacks"
branch_labels = None
depends_on = None
PK = ["user_id", "kind", "team_id"]


def _backfill(bind) -> None:
    rows = bind.execute(sa.text("SELECT user_id FROM channel_identities WHERE kind = 'slack' AND team_id = ''")).fetchall()
    pick = sa.text("SELECT team_id FROM approval_channels WHERE kind = 'slack' AND team_id IS NOT NULL AND "
                   "((scope = 'user' AND owner = :u) OR scope = 'org') ORDER BY CASE WHEN scope = 'user' THEN 0 ELSE 1 END, created LIMIT 1")
    for (uid,) in rows:
        team = bind.execute(pick, {"u": uid}).scalar()
        if team: bind.execute(sa.text("UPDATE channel_identities SET team_id = :t WHERE user_id = :u AND kind = 'slack' AND team_id = ''"), {"t": team, "u": uid})


def upgrade() -> None:
    bind = op.get_bind(); insp = sa.inspect(bind)
    if "team_id" not in {c["name"] for c in insp.get_columns("channel_identities")}:
        with op.batch_alter_table("channel_identities") as b:
            b.add_column(sa.Column("team_id", sa.Text, nullable=False, server_default=""))
    pk = insp.get_pk_constraint("channel_identities")
    if pk.get("constrained_columns") != PK:
        with op.batch_alter_table("channel_identities", recreate="always") as b:
            if pk.get("name"): b.drop_constraint(pk["name"], type_="primary")
            b.create_primary_key("pk_channel_identities", PK)
    _backfill(bind)


def downgrade() -> None:
    with op.batch_alter_table("channel_identities", recreate="always") as b:
        b.drop_constraint("pk_channel_identities", type_="primary")
        b.create_primary_key("pk_channel_identities", ["user_id", "kind"])
        b.drop_column("team_id")
