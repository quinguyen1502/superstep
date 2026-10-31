"""Alembic migrations on a fresh Postgres database (TASK-0009).

Runs when TEST_DATABASE_URL (or DATABASE_URL) points at Postgres; the role needs CREATEDB.
A throwaway database is created and dropped, so the configured one is never touched."""
import os, uuid
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from app.core.config import normalise_db_url
from app.models.database import Database
from app.services.seed import bootstrap
from app.models.database import head_revision

HEAD = head_revision()

URL = normalise_db_url(os.environ.get("TEST_DATABASE_URL") or os.environ.get("DATABASE_URL") or "")
pytestmark = pytest.mark.skipif(not URL.startswith("postgresql"), reason="set TEST_DATABASE_URL=postgresql://... to run")


@pytest.fixture
def fresh_pg():
    name = f"lgs_test_{uuid.uuid4().hex[:8]}"
    admin = create_engine(make_url(URL).set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as c: c.execute(text(f'CREATE DATABASE "{name}"'))
    db = Database(make_url(URL).set(database=name).render_as_string(hide_password=False))
    try: yield db
    finally:
        db.engine.dispose()
        with admin.connect() as c: c.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        admin.dispose()


def test_migrations_and_seed_on_fresh_postgres(fresh_pg):
    bootstrap(fresh_pg); bootstrap(fresh_pg)  # second run is a no-op (idempotent upgrade + seed)
    insp = inspect(fresh_pg.engine)
    assert fresh_pg.engine.dialect.name == "postgresql"
    assert {"users", "workflows", "runs", "credentials", "alembic_version"} <= set(insp.get_table_names())
    with fresh_pg.engine.connect() as c:
        assert c.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == HEAD
        assert c.execute(text("SELECT count(*) FROM users WHERE email='admin@example.com'")).scalar_one() == 1
        assert c.execute(text("SELECT count(*) FROM workflows")).scalar_one() >= 1


def test_pat_name_index_on_postgres(fresh_pg):
    """TASK-0213: active duplicates are renamed before the partial unique index, which then refuses a second active name."""
    import sqlalchemy as sa
    from alembic import command
    from alembic.config import Config
    from app.models.database import MIGRATIONS_DIR
    cfg = Config(); cfg.set_main_option("script_location", os.path.normpath(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", fresh_pg.url.replace("%", "%%"))
    command.upgrade(cfg, "0049_review_recovery")
    with fresh_pg.engine.begin() as c:
        for tid, name, created, revoked in [("a", "ci", 1, None), ("b", "ci", 2, None), ("c", "ci", 0, 3.0)]:
            c.execute(text("INSERT INTO personal_access_tokens (id, user_id, name, token_hash, prefix, created, revoked) "
                           "VALUES (:i, 'u1', :n, :i, 'pat_', :c, :r)"), dict(i=tid, n=name, c=created, r=revoked))
    command.upgrade(cfg, "head")
    with fresh_pg.engine.connect() as c:
        assert dict(c.execute(text("SELECT id, name FROM personal_access_tokens")).fetchall()) == {"a": "ci", "b": "ci (2)", "c": "ci"}
    with pytest.raises(sa.exc.IntegrityError), fresh_pg.engine.begin() as c:
        c.execute(text("INSERT INTO personal_access_tokens (id, user_id, name, token_hash, prefix, created) VALUES ('d', 'u1', 'ci', 'd', 'pat_', 9)"))
    with fresh_pg.engine.begin() as c:  # a revoked row does not block the name
        c.execute(text("INSERT INTO personal_access_tokens (id, user_id, name, token_hash, prefix, created, revoked) VALUES ('e', 'u1', 'ci', 'e', 'pat_', 9, 10)"))
