"""cron expressions, schedule API, and the scheduler in the run worker."""
import time, uuid
from datetime import datetime
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient
from app.api.deps import get_db, schedule_service
from app.main import app
from app.repositories import ScheduleRepository, UserRepository
from app.services import cron


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client:  # lifespan starts the in-process worker, which fires due schedules
        yield client

def H(t): return {"Authorization": f"Bearer {t}"}
def user(c):
    return c.post("/api/auth/register", json={"email": f"sc{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]["token"]
def example(c, tok): return c.get("/api/workflows", headers=H(tok)).json()["data"][0]["id"]
def at(y, mo, d, h, mi, tz="Asia/Ho_Chi_Minh"): return datetime(y, mo, d, h, mi, tzinfo=ZoneInfo(tz)).timestamp()
def local(ts, tz="Asia/Ho_Chi_Minh"): return datetime.fromtimestamp(ts, ZoneInfo(tz)).strftime("%a %m-%d %H:%M")


# ---------- cron ----------
@pytest.mark.parametrize("expr,want", [
    ("*/15 * * * *", ["Sun 10-18 10:15", "Sun 10-18 10:30", "Sun 10-18 10:45"]),
    ("0 9 * * MON-FRI", ["Mon 10-19 09:00", "Tue 10-20 09:00", "Wed 10-21 09:00"]),
    ("@daily", ["Mon 10-19 00:00", "Tue 10-20 00:00", "Wed 10-21 00:00"]),
    ("0 9 1,15 * mon", ["Mon 10-19 09:00", "Mon 10-26 09:00", "Sun 11-01 09:00"]),  # both day fields: either matches
    ("30 8 * * 7", ["Sun 10-25 08:30", "Sun 11-01 08:30", "Sun 11-08 08:30"]),      # 7 is Sunday
    ("0 0 1 JAN,jul *", ["Fri 01-01 00:00", "Thu 07-01 00:00", "Sat 01-01 00:00"]),
    ("5/20 10 * * *", ["Sun 10-18 10:25", "Sun 10-18 10:45", "Mon 10-19 10:05"]),
])
def test_cron_next_times(expr, want):
    assert [local(t) for t in cron.upcoming(expr, "Asia/Ho_Chi_Minh", at(2026, 10, 18, 10, 7), 3)] == want


def test_cron_dst_skipped_and_repeated_hours():
    ny = "America/New_York"
    assert [local(t, ny) for t in cron.upcoming("30 2 * * *", ny, at(2026, 3, 7, 12, 0, ny), 2)] == ["Sun 03-08 03:30", "Mon 03-09 02:30"]
    fall = cron.upcoming("30 1 * * *", ny, at(2026, 10, 31, 12, 0, ny), 2)
    assert [local(t, ny) for t in fall] == ["Sun 11-01 01:30", "Mon 11-02 01:30"] and fall[1] - fall[0] == 25 * 3600  # once, not twice


@pytest.mark.parametrize("expr,msg", [("* * *", "five fields"), ("61 * * * *", "minute: values must be 0-59"), ("*/0 * * * *", "step"),
                                      ("5-1 * * * *", "backwards"), ("* * * FOO *", "month: 'FOO'"), ("* 24 * * *", "hour")])
def test_cron_errors_name_the_field(expr, msg):
    with pytest.raises(cron.CronError, match=msg): cron.parse(expr)


def test_unknown_time_zone():
    with pytest.raises(cron.CronError, match="Mars/Base"): cron.zone("Mars/Base")


# ---------- API ----------
def test_schedule_crud_preview_and_access(c):
    tok = user(c); wid = example(c, tok)
    r = c.post(f"/api/workflows/{wid}/schedules", json={"name": "bad", "cron": "61 * * * *"}, headers=H(tok))
    assert r.status_code == 400 and r.json()["error"]["code"] == "SCHEDULE_CRON_INVALID" and "minute" in r.json()["error"]["message"]
    r = c.post(f"/api/workflows/{wid}/schedules", json={"cron": "@daily", "timezone": "Mars/Base"}, headers=H(tok))
    assert r.json()["error"]["code"] == "SCHEDULE_CRON_INVALID"
    s = c.post(f"/api/workflows/{wid}/schedules", json={"name": "Morning", "cron": "0 9 * * MON-FRI", "timezone": "Asia/Ho_Chi_Minh",
                                                       "input": {"message": "status report"}}, headers=H(tok)).json()["data"]
    assert s["enabled"] and len(s["next_runs"]) == 3 and s["next_runs"][0] > time.time() and s["input"] == {"message": "status report"}
    assert [x["id"] for x in c.get(f"/api/workflows/{wid}/schedules", headers=H(tok)).json()["data"]] == [s["id"]]
    off = c.patch(f"/api/workflows/{wid}/schedules/{s['id']}", json={"enabled": False}, headers=H(tok)).json()["data"]
    assert off["enabled"] is False and off["next_runs"] == []
    on = c.patch(f"/api/workflows/{wid}/schedules/{s['id']}", json={"enabled": True, "cron": "@hourly"}, headers=H(tok)).json()["data"]
    assert on["cron"] == "@hourly" and datetime.fromtimestamp(on["next_runs"][0]).minute == 0
    other = user(c)
    assert c.get(f"/api/workflows/{wid}/schedules", headers=H(other)).json()["error"]["code"] == "WORKFLOW_NOT_FOUND"
    assert c.delete(f"/api/workflows/{wid}/schedules/{s['id']}", headers=H(other)).status_code == 404
    pv = c.post("/api/schedules/preview", json={"cron": "*/5 * * * *", "timezone": "UTC"}, headers=H(tok)).json()["data"]["next_runs"]
    assert len(pv) == 5 and all(b - a == 300 for a, b in zip(pv, pv[1:]))
    assert c.delete(f"/api/workflows/{wid}/schedules/{s['id']}", headers=H(tok)).json()["data"] == {"ok": True}
    assert c.patch(f"/api/workflows/{wid}/schedules/{s['id']}", json={"enabled": True}, headers=H(tok)).json()["error"]["code"] == "SCHEDULE_NOT_FOUND"


def test_limit_per_workflow(c, monkeypatch):
    from app.services import schedule_service as mod
    monkeypatch.setattr(mod, "MAX_PER_WORKFLOW", 2)
    tok = user(c); wid = example(c, tok)
    for _ in range(2): c.post(f"/api/workflows/{wid}/schedules", json={"cron": "@daily"}, headers=H(tok))
    r = c.post(f"/api/workflows/{wid}/schedules", json={"cron": "@daily"}, headers=H(tok))
    assert r.json()["error"]["code"] == "SCHEDULE_LIMIT" and r.json()["error"]["details"]["max"] == 2


# ---------- scheduler ----------
def _make_due(sid): ScheduleRepository(get_db()).set_fields(sid, next_run=time.time() - 5)


def test_worker_runs_a_due_schedule_once(c):
    tok = user(c); wid = example(c, tok)
    s = c.post(f"/api/workflows/{wid}/schedules", json={"name": "now", "cron": "0 0 1 1 *", "input": {"message": "where is my order A100"}}, headers=H(tok)).json()["data"]
    _make_due(s["id"])
    for _ in range(100):
        runs = [r for r in c.get(f"/api/workflows/{wid}/runs", headers=H(tok)).json()["data"] if r.get("source") == "schedule"]
        if runs and runs[0]["status"] not in ("queued", "running"): break
        time.sleep(0.1)
    assert len(runs) == 1 and runs[0]["status"] == "ok" and runs[0]["input"] == {"message": "where is my order A100"}
    row = ScheduleRepository(get_db()).get(s["id"])
    assert row.last_run_id == runs[0]["id"] and row.next_run > time.time() + 86400  # moved on to next January
    assert schedule_service().fire_due() == []  # nothing due any more


def test_two_schedulers_do_not_both_fire(c):
    tok = user(c); wid = example(c, tok)
    s = c.post(f"/api/workflows/{wid}/schedules", json={"cron": "0 0 1 1 *", "enabled": True}, headers=H(tok)).json()["data"]
    repo = ScheduleRepository(get_db()); row = repo.get(s["id"]); seen = time.time() - 5; repo.set_fields(s["id"], next_run=seen)
    assert repo.claim(s["id"], seen, row.next_run, time.time()) is True
    assert repo.claim(s["id"], seen, row.next_run, time.time()) is False  # the second worker saw the same row and loses


def test_scheduler_stops_when_the_owner_loses_access_and_drops_deleted_workflows(c):
    tok = user(c); wid = example(c, tok); me = c.get("/api/me", headers=H(tok)).json()["data"]["id"]
    s = c.post(f"/api/workflows/{wid}/schedules", json={"cron": "0 0 1 1 *"}, headers=H(tok)).json()["data"]
    UserRepository(get_db()).set_active(me, False)  # a deactivated creator no longer has the workflow's "share" right
    repo = ScheduleRepository(get_db()); _make_due(s["id"]); schedule_service().fire_due()
    row = repo.get(s["id"]); assert row.enabled is False and row.next_run is None and row.note == "access"
    UserRepository(get_db()).set_active(me, True)

    tok2 = user(c); wid2 = c.post("/api/workflows", json={"name": f"gone {uuid.uuid4().hex[:4]}", "state": [], "nodes": [], "edges": []}, headers=H(tok2)).json()["data"]["id"]
    s2 = c.post(f"/api/workflows/{wid2}/schedules", json={"cron": "@daily"}, headers=H(tok2)).json()["data"]
    c.delete(f"/api/workflows/{wid2}", headers=H(tok2)); _make_due(s2["id"]); schedule_service().fire_due()
    assert repo.get(s2["id"]) is None


def test_zones_resolve_without_system_zone_data(tmp_path):
    """The `tzdata` package backs zoneinfo when the image has no /usr/share/zoneinfo (browsers in Vietnam send Asia/Saigon)."""
    import os, subprocess, sys
    code = "from app.services import cron; print(cron.zone('Asia/Saigon').key, cron.zone('Asia/Ho_Chi_Minh').key)"
    out = subprocess.run([sys.executable, "-c", code], env={**os.environ, "PYTHONTZPATH": str(tmp_path)},
                         cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))), capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    assert out.stdout.split() == ["Asia/Saigon", "Asia/Ho_Chi_Minh"]
