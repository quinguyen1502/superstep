"""follow-up: one verified owner per chat account (kind, workspace, external id).

A partial unique index (WHERE verified_at IS NOT NULL) closes the verify race; works on SQLite and Postgres.
Existing duplicates (possible before this index) keep the earliest verification; the others go back to unverified."""
from alembic import op
import sqlalchemy as sa

revision = "0017_verified_identity_unique"
down_revision = "0016_identity_workspaces"
NAME = "uq_channel_identities_verified"


def upgrade():
    bind = op.get_bind()
    if NAME in {i["name"] for i in sa.inspect(bind).get_indexes("channel_identities")}: return
    rows = bind.execute(sa.text("SELECT user_id, kind, team_id, external_id FROM channel_identities "
                                "WHERE verified_at IS NOT NULL ORDER BY verified_at, user_id")).fetchall()
    seen = set()
    for u, k, t, e in rows:
        if (k, t, e) in seen:
            bind.execute(sa.text("UPDATE channel_identities SET verified_at = NULL WHERE user_id = :u AND kind = :k AND team_id = :t"), {"u": u, "k": k, "t": t})
        seen.add((k, t, e))
    where = sa.text("verified_at IS NOT NULL")
    op.create_index(NAME, "channel_identities", ["kind", "team_id", "external_id"], unique=True, sqlite_where=where, postgresql_where=where)


def downgrade():
    op.drop_index(NAME, table_name="channel_identities")
