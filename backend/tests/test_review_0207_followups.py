"""TASK-0208: the two minor points of the review of #262. A body without a length that passes the ceiling on a route
that parses JSON or a file answers 413 like a declared one, and a CLI sign-in whose token name was taken between
approval and collection still delivers a token instead of being left consumed."""
from fastapi.testclient import TestClient
from app.main import app

c = TestClient(app)
MB = 1024 * 1024


def _chunks(total):
    for _ in range(total // MB): yield b"x" * MB


def test_a_chunked_body_past_the_ceiling_on_a_json_route_answers_413():
    r = c.post("/api/auth/login", content=_chunks(12 * MB), headers={"content-type": "application/json"})
    assert r.status_code == 413, r.text
    assert r.json()["success"] is False and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_a_chunked_body_past_the_ceiling_on_a_callback_still_answers_413():
    r = c.post("/api/channels/events/slack", content=_chunks(2 * MB), headers={"content-type": "application/json"})
    assert r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"


def test_a_name_taken_between_approval_and_collection_gets_a_free_name(tmp_path):
    from app.models import User
    from app.models.database import Database
    from app.repositories import CliDeviceRepository, PersonalAccessTokenRepository, UserRepository
    from app.services.pat_service import PatService
    db = Database(f"sqlite:///{tmp_path}/p.db"); db.migrate()
    users, pats, devices = UserRepository(db), PersonalAccessTokenRepository(db), CliDeviceRepository(db)
    with db.session() as s: s.add(User(id="u1", email="u1@example.com", password="x", created=0)); s.commit()
    svc = PatService(pats, devices, users)
    started = svc.start_device()
    assert svc.approve("u1", started["user_code"], "laptop")["name"] == "laptop"
    svc.create("u1", "laptop"); svc.create("u1", "laptop (2)")  # taken after approval, before the CLI polls
    got = svc.poll(started["device_code"])
    assert got["status"] == "approved" and got["token"].startswith("pat_")
    names = sorted(p.name for p in pats.list_active("u1"))
    assert names == ["laptop", "laptop (2)", "laptop (3)"]


def test_a_free_name_stays_within_the_name_limit(tmp_path):
    from app.models import User
    from app.models.database import Database
    from app.repositories import CliDeviceRepository, PersonalAccessTokenRepository, UserRepository
    from app.services.pat_service import NAME_MAX, PatService
    db = Database(f"sqlite:///{tmp_path}/p.db"); db.migrate()
    users, pats, devices = UserRepository(db), PersonalAccessTokenRepository(db), CliDeviceRepository(db)
    with db.session() as s: s.add(User(id="u1", email="u1@example.com", password="x", created=0)); s.commit()
    svc = PatService(pats, devices, users)
    long = "n" * NAME_MAX
    started = svc.start_device(); svc.approve("u1", started["user_code"], long)
    svc.create("u1", long)
    svc.poll(started["device_code"])
    fresh = [p.name for p in pats.list_active("u1") if p.name != long]
    assert len(fresh) == 1 and len(fresh[0]) <= NAME_MAX and fresh[0].endswith(" (2)")
