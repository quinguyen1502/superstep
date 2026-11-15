"""follow-up: 0016 backfills the Slack workspace of existing identities (SQLite always, Postgres when configured)."""
import os, uuid
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from app.core.config import normalise_db_url
from app.models.database import MIGRATIONS_DIR, Database

PG = normalise_db_url(os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL") or "")


def upgrade(db: Database, rev: str) -> None:
    cfg = Config(); cfg.set_main_option("script_location", os.path.normpath(MIGRATIONS_DIR))
    with db.engine.begin() as conn: cfg.attributes["connection"] = conn; command.upgrade(cfg, rev)


@pytest.fixture(params=["sqlite", "postgresql"])
def db(request, tmp_path):
    if request.param == "sqlite": yield Database(f"sqlite:///{tmp_path / 'm.db'}"); return
    if not PG.startswith("postgresql"): pytest.skip("set TEST_DATABASE_URL=postgresql://... to run")
    name = f"lgs_mig_{uuid.uuid4().hex[:8]}"; admin = create_engine(make_url(PG).set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c: c.execute(text(f'CREATE DATABASE "{name}"'))
    d = Database(make_url(PG).set(database=name).render_as_string(hide_password=False))
    try: yield d
    finally:
        d.engine.dispose()
        with admin.connect() as c: c.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()


def test_identity_workspace_backfill(db):
    upgrade(db, "0015_run_callbacks")
    with db.engine.begin() as c:
        ch = "INSERT INTO approval_channels(id, owner, kind, secrets, hint, created, scope, name, team_id) VALUES (:i, :o, :k, 'x', 'h', :t, :s, NULL, :team)"
        for row in (("org1", "adm", "slack", 1.0, "org", "TORG"), ("own1", "u1", "slack", 5.0, "user", "TOWN"), ("tg1", "u1", "telegram", 1.0, "user", "777")):
            c.execute(text(ch), dict(zip(("i", "o", "k", "t", "s", "team"), row)))
        idn = "INSERT INTO channel_identities(user_id, kind, external_id, created, verified_at, code_attempts) VALUES (:u, :k, :e, 1.0, 2.0, 0)"
        for u, k, e in (("u1", "slack", "U1"), ("u2", "slack", "U2"), ("u1", "telegram", "11")):
            c.execute(text(idn), {"u": u, "k": k, "e": e})
    upgrade(db, "head")
    with db.engine.connect() as c:
        got = {(r.user_id, r.kind): r.team_id for r in c.execute(text("SELECT user_id, kind, team_id FROM channel_identities"))}
    assert got == {("u1", "slack"): "TOWN", ("u2", "slack"): "TORG", ("u1", "telegram"): ""}  # personal first, else org; Telegram has none
    assert inspect(db.engine).get_pk_constraint("channel_identities")["constrained_columns"] == ["user_id", "kind", "team_id"]
    upgrade(db, "head")  # idempotent


def test_verified_duplicates_are_resolved_then_the_index_holds(db):
    import sqlalchemy.exc
    upgrade(db, "0016_identity_workspaces")
    ins = text("INSERT INTO channel_identities(user_id, kind, team_id, external_id, created, verified_at, code_attempts) VALUES (:u, 'slack', 'T1', 'U1', 1.0, :v, 0)")
    with db.engine.begin() as c:
        for u, v in (("late", 9.0), ("first", 3.0), ("pending", None)): c.execute(ins, {"u": u, "v": v})
    upgrade(db, "head")
    with db.engine.connect() as c:
        assert [r[0] for r in c.execute(text("SELECT user_id FROM channel_identities WHERE verified_at IS NOT NULL"))] == ["first"]
    with pytest.raises(sqlalchemy.exc.IntegrityError), db.engine.begin() as c:
        c.execute(text("UPDATE channel_identities SET verified_at = 10.0 WHERE user_id = 'pending'"))
