"""TASK-0213: active token names are unique per user in the database, not only by a check before the insert (REV-0196).
A create that loses the race answers PAT_NAME_TAKEN; the token minted at CLI collection takes the next free name."""
import threading
import pytest
import sqlalchemy as sa
from app.core.errors import AppError
from app.models import User
from app.models.database import Database
from app.repositories import CliDeviceRepository, PersonalAccessTokenRepository, UserRepository
from app.services.pat_service import PatService


def _svc(tmp_path):
    db = Database(f"sqlite:///{tmp_path}/p.db"); db.migrate()
    users, pats, devices = UserRepository(db), PersonalAccessTokenRepository(db), CliDeviceRepository(db)
    with db.session() as s:
        s.add(User(id="u1", email="u1@example.com", password="x", created=0))
        s.add(User(id="u2", email="u2@example.com", password="x", created=0)); s.commit()
    return db, pats, PatService(pats, devices, users)


def _stale(pats, monkeypatch, misses):
    """The check before the insert sees no token for the first `misses` calls: what a create at the same moment sees."""
    real, left = pats.active_by_name, [misses]
    def fake(user_id, name):
        if left[0] > 0: left[0] -= 1; return None
        return real(user_id, name)
    monkeypatch.setattr(pats, "active_by_name", fake)


def test_a_create_that_loses_the_race_answers_pat_name_taken(tmp_path, monkeypatch):
    _, pats, svc = _svc(tmp_path)
    svc.create("u1", "ci")
    _stale(pats, monkeypatch, 1)
    with pytest.raises(AppError) as err: svc.create("u1", "ci")
    assert err.value.code == "PAT_NAME_TAKEN" and err.value.status == 409
    assert [p.name for p in pats.list_active("u1")] == ["ci"]


def test_parallel_creates_with_one_name_make_one_token(tmp_path):
    _, pats, svc = _svc(tmp_path)
    barrier, results = threading.Barrier(8), []
    def go():
        barrier.wait()
        try: svc.create("u1", "same"); results.append("ok")
        except AppError as exc: results.append(exc.code)
    threads = [threading.Thread(target=go) for _ in range(8)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert results.count("ok") == 1 and set(results) <= {"ok", "PAT_NAME_TAKEN"}
    assert [p.name for p in pats.list_active("u1")] == ["same"]


def test_cli_collection_that_loses_the_race_takes_the_next_free_name(tmp_path, monkeypatch):
    _, pats, svc = _svc(tmp_path)
    started = svc.start_device(); svc.approve("u1", started["user_code"], "laptop")
    svc.create("u1", "laptop")
    _stale(pats, monkeypatch, 2)  # _free_name and _issue both miss the token created at the same moment
    got = svc.poll(started["device_code"])
    assert got["status"] == "approved" and got["token"].startswith("pat_")
    assert sorted(p.name for p in pats.list_active("u1")) == ["laptop", "laptop (2)"]


def test_names_can_still_be_reused_after_revoke_and_by_another_user(tmp_path):
    _, pats, svc = _svc(tmp_path)
    first = svc.create("u1", "ci"); svc.revoke("u1", first["id"])
    svc.create("u1", "ci"); svc.create("u2", "ci")
    second = svc.list("u1")["items"][0]; svc.revoke("u1", second["id"]); svc.create("u1", "ci")
    assert [p.name for p in pats.list_active("u1")] == ["ci"]


def test_migration_renames_active_duplicates_and_keeps_revoked_ones(tmp_path):
    import os
    from alembic import command
    from alembic.config import Config
    from app.models.database import MIGRATIONS_DIR
    db = Database(f"sqlite:///{tmp_path}/m.db")
    cfg = Config(); cfg.set_main_option("script_location", os.path.normpath(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", db.url)
    command.upgrade(cfg, "0049_review_recovery")
    rows = [("a", "u1", "ci", 1, None), ("b", "u1", "ci", 2, None), ("c", "u1", "ci (2)", 3, None), ("d", "u1", "ci", 4, None),
            ("e", "u1", "ci", 0, 5.0), ("f", "u2", "ci", 1, None)]
    with db.engine.begin() as conn:
        for tid, uid, name, created, revoked in rows:
            conn.execute(sa.text("INSERT INTO personal_access_tokens (id, user_id, name, token_hash, prefix, created, revoked) "
                                 "VALUES (:i, :u, :n, :h, 'pat_', :c, :r)"), dict(i=tid, u=uid, n=name, h=tid, c=created, r=revoked))
    command.upgrade(cfg, "head")
    with db.engine.connect() as conn:
        got = dict(conn.execute(sa.text("SELECT id, name FROM personal_access_tokens")).fetchall())
    assert got == {"a": "ci", "b": "ci (3)", "c": "ci (2)", "d": "ci (4)", "e": "ci", "f": "ci"}
    with pytest.raises(sa.exc.IntegrityError), db.engine.begin() as conn:
        conn.execute(sa.text("INSERT INTO personal_access_tokens (id, user_id, name, token_hash, prefix, created) "
                             "VALUES ('g', 'u1', 'ci', 'g', 'pat_', 9)"))
