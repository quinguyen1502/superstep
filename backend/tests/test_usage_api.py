"""Admin usage API: exact aggregates from run columns, product health counts, permissions, migration and gauges."""
import os, time, uuid
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from app.core.config import normalise_db_url

from app.main import app
from app.models import Run
from app.models.approval import ApprovalWait
from app.models.database import Database, MIGRATIONS_DIR
from app.models.webhook_delivery import WebhookDelivery
from app.models.workflow import Workflow
from app.models.workflow_schedule import WorkflowSchedule
from app.repositories.usage import UsageRepository
from app.schemas.usage import UsageHealth, UsageSummary
from app.services import job_queue as jq
from app.services.health_probes import Probes
from app.services.run_bus import InMemoryRunBus
from app.services.run_worker import RunWorker
from app.services.telemetry import Telemetry
from app.services.usage_service import UsageService

c = TestClient(app)
def H(t): return {"Authorization": f"Bearer {t}"}
def admin(): return c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]
def editor():
    return c.post("/api/auth/register", json={"email": f"u{uuid.uuid4().hex[:8]}@example.com", "password": "secret12"}).json()["data"]["token"]


PG = normalise_db_url(os.environ.get("TEST_DATABASE_URL") or "")


@pytest.fixture(params=["sqlite", "postgres"])
def db(request, tmp_path):
    """A fresh database per test: SQLite, and Postgres when TEST_DATABASE_URL points at one (a throwaway database)."""
    if request.param == "sqlite":
        d = Database(f"sqlite:///{tmp_path / 'usage.db'}"); d.migrate(); yield d; d.engine.dispose(); return
    if not PG.startswith("postgresql"): pytest.skip("set TEST_DATABASE_URL=postgresql://... to run")
    name = f"usage_{uuid.uuid4().hex[:8]}"
    root = create_engine(make_url(PG).set(database="postgres"), isolation_level="AUTOCOMMIT")
    with root.connect() as conn: conn.execute(text(f'CREATE DATABASE "{name}"'))
    d = Database(make_url(PG).set(database=name).render_as_string(hide_password=False))
    try: d.migrate(); yield d
    finally:
        d.engine.dispose()
        with root.connect() as conn: conn.execute(text(f'DROP DATABASE IF EXISTS "{name}"'))
        root.dispose()


def add(s, **kw): s.add(Run(id=uuid.uuid4().hex[:10], events="[]", **kw))


def seed(db, now):
    with db.session() as s:
        s.add(Workflow(id="wa", name="Alpha", data="{}", updated=now, owner="u"))
        h = 3600
        add(s, workflow_id="wa", status="ok", started=now - 2 * h, tokens_in=100, tokens_out=50, cost_usd=0.01)
        add(s, workflow_id="wa", status="ok", started=now - 2 * h, tokens_in=10, tokens_out=5, cost_usd=None)  # unpriced
        add(s, workflow_id="wa", status="error", started=now - 30 * h, tokens_in=1, tokens_out=1, cost_usd=0.0)
        add(s, workflow_id="gone", status="timeout", started=now - 3 * 86400, tokens_in=0, tokens_out=0, cost_usd=0.5)  # deleted workflow
        add(s, workflow_id="wa", status="waiting", started=now - h)  # not finished: never unpriced
        add(s, workflow_id="wa", status="ok", started=now - h, tokens_in=999, tokens_out=999, cost_usd=9.0, parent_run_id="p", parent_step="s")  # child
        add(s, workflow_id="wa", status="ok", started=now - 40 * 86400, tokens_in=5, tokens_out=5, cost_usd=1.0)  # outside 30d
        s.commit()


def test_summary_is_exact(db):
    now = time.time(); seed(db, now); svc = UsageService(UsageRepository(db))
    day = svc.summary("x", "24h")
    assert day["bucket"] == "hour" and len(day["series"]) == 24
    t = day["totals"]
    assert t["runs"] == 3 and t["by_status"] == {"ok": 2, "waiting": 1} and t["tokens_in"] == 110 and t["tokens_out"] == 55
    assert t["cost_usd"] == pytest.approx(0.01) and t["unpriced_runs"] == 1 and t["unpriced_share"] == 0.5 and t["success_rate"] == 1.0
    assert sum(b["ok"] for b in day["series"]) == 2 and sum(b["other"] for b in day["series"]) == 1
    assert day["series"][22]["ok"] == 2 and day["series"][23]["other"] == 1  # 2 h and 1 h before now
    week = svc.summary("x", "7d")
    w = week["totals"]
    assert week["bucket"] == "day" and len(week["series"]) == 7
    assert w["runs"] == 5 and w["by_status"] == {"ok": 2, "error": 1, "timeout": 1, "waiting": 1}
    assert w["cost_usd"] == pytest.approx(0.51) and w["unpriced_runs"] == 1 and w["unpriced_share"] == 0.25 and w["success_rate"] == 0.5
    top = {x["workflow_id"]: x for x in week["top_workflows"]}
    assert top["wa"]["name"] == "Alpha" and top["wa"]["runs"] == 4 and top["wa"]["errors"] == 1 and top["wa"]["error_rate"] == 0.25
    assert top["wa"]["unpriced_runs"] == 1 and top["gone"]["name"] is None and top["gone"]["errors"] == 1
    assert [x["workflow_id"] for x in week["top_workflows"]] == ["wa", "gone"]
    assert [x["workflow_id"] for x in svc.summary("x", "7d", sort="cost")["top_workflows"]] == ["gone", "wa"]
    assert svc.summary("x", "7d", bucket="hour")["series"].__len__() == 168
    UsageSummary.model_validate(week)


def test_health_counts_are_exact(db):
    now = time.time(); svc = UsageService(UsageRepository(db))
    with db.session() as s:
        for i, (status, outcome, created, closed) in enumerate([("waiting", None, now - 600, None), ("waiting", None, now - 60, None),
                                                                 ("closed", "expired", now - 9000, now - 100), ("closed", "expired", now - 9 * 86400, now - 8 * 86400),
                                                                 ("closed", "answered", now - 50, now - 10)]):
            s.add(ApprovalWait(id=f"a{i}", run_id=f"r{i}", node_id="h", owner="u", status=status, outcome=outcome, created=created, closed_at=closed))
        for i, (status, updated) in enumerate([("failed", now - 100), ("failed", now - 10 * 86400), ("retrying", now - 5), ("ok", now - 5)]):
            s.add(WebhookDelivery(id=f"d{i}", workflow_id="w", url="https://x", event="run.finished", payload="{}", status=status, created=updated, updated=updated))
        for i, (enabled, next_run, note) in enumerate([(True, now - 3600, None), (True, now + 60, None), (True, now - 10, None),
                                                       (False, None, "unknown time zone 'Asia/Saigon'"), (False, None, None)]):
            s.add(WorkflowSchedule(id=f"s{i}", workflow_id="w", owner="u", name=f"S{i}", cron="@daily", timezone="UTC", input="{}",
                                   enabled=enabled, next_run=next_run, note=note, created=now - i))
        s.commit()
    h = svc.counts(now - 7 * 86400, now)
    assert h["approvals"]["waiting"] == 2 and 599 <= h["approvals"]["oldest_age_s"] <= 601 and h["approvals"]["expired"] == 1
    assert h["webhooks"] == {"failed": 1, "retrying": 1}
    assert h["schedules"]["overdue"] == 1 and h["schedules"]["disabled"] == 1
    assert h["schedules"]["disabled_list"] == [{"id": "s3", "workflow_id": "w", "name": "S3", "note": "unknown time zone 'Asia/Saigon'"}]
    UsageHealth.model_validate(h)
    # the worker's gauges report the same values
    reader = InMemoryMetricReader(); t = Telemetry(exporters=[], metric_readers=[reader])
    class Db:
        def ping(self): return True
    class Runs:
        def oldest_started(self, status): return None
    q = jq.InMemoryJobQueue()
    t.watch(Probes(Db(), Runs(), q, InMemoryRunBus(), False, False), RunWorker(q, lambda: None), product=lambda: svc.counts(now - 7 * 86400, now))
    data = reader.get_metrics_data()
    pts = {m.name: m.data.data_points[0].value for rm in data.resource_metrics for sm in rm.scope_metrics for m in sm.metrics}
    assert pts["studio.approvals.waiting"] == 2 and pts["studio.webhooks.failed"] == 1 and pts["studio.webhooks.retrying"] == 1
    assert pts["studio.schedules.overdue"] == 1 and pts["studio.schedules.disabled"] == 1 and pts["studio.approvals.oldest_age"] >= 599


def test_api_needs_users_manage():
    r = c.get("/api/admin/usage", headers=H(editor()))
    assert r.status_code == 403 and r.json()["error"]["code"] == "PERMISSION_DENIED"
    assert c.get("/api/admin/usage/health", headers=H(editor())).status_code == 403
    assert c.get("/api/admin/usage").status_code == 401


def test_api_answers_admins(monkeypatch):
    monkeypatch.setenv("STUDIO_GRAFANA_URL", "https://grafana.example.com/")
    tok = admin()
    r = c.get("/api/admin/usage?window=24h", headers=H(tok)); body = r.json()["data"]
    assert r.status_code == 200 and body["window"] == "24h" and body["grafana_url"] == "https://grafana.example.com"
    UsageSummary.model_validate(body)
    UsageHealth.model_validate(c.get("/api/admin/usage/health", headers=H(tok)).json()["data"])
    assert c.get("/api/admin/usage?window=1y", headers=H(tok)).status_code == 422
    monkeypatch.delenv("STUDIO_GRAFANA_URL")
    assert c.get("/api/admin/usage", headers=H(tok)).json()["data"]["grafana_url"] is None


def test_migration_upgrades_and_downgrades(tmp_path):
    db = Database(f"sqlite:///{tmp_path / 'm.db'}")
    cfg = Config(); cfg.set_main_option("script_location", os.path.normpath(MIGRATIONS_DIR))
    with db.engine.begin() as conn:
        cfg.attributes["connection"] = conn
        command.upgrade(cfg, "head")
        assert {"ix_runs_started", "ix_runs_status_started"} <= {i["name"] for i in inspect(conn).get_indexes("runs")}
        command.downgrade(cfg, "0058_browser_approvals")
        assert "ix_runs_started" not in {i["name"] for i in inspect(conn).get_indexes("runs")}
        command.upgrade(cfg, "head")
    db.engine.dispose()
