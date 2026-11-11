"""Per-run model usage rows, the Usage page's models, users, teams and chat refusal blocks, and the chat index."""
import ast, os, pathlib, time, uuid
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from app.engine.usage import make_usage
from app.main import app
from app.models import Run, Team, TeamMember, User, Workflow
from app.models.chat_message import ChatMessage
from app.models.database import Database, MIGRATIONS_DIR
from app.models.run_usage import RunUsage
from app.repositories import RunRepository, RunUsageRepository
from app.repositories.usage import UsageRepository
from app.schemas.usage import UsageHealth, UsageSummary
from app.services import run_usage
from app.services.run_service import RunService
from app.services.telemetry import LABELS, summarize
from app.services.usage_service import UsageService

APP = pathlib.Path(__file__).resolve().parents[1] / "app"


@pytest.fixture
def db(tmp_path):
    d = Database(f"sqlite:///{tmp_path / 'u.db'}"); d.migrate(); yield d; d.engine.dispose()


def emb(model, tokens, cost):
    return {**make_usage("openai", model, tokens, 0), "kind": "embedding", "cost_usd": cost}


def three_node_events():
    a = {**make_usage("openai", "gpt-4o", 1000, 200), "duration_ms": 120.0}
    b = make_usage("ollama", "llama3.2", 50, 20)  # unpriced
    return [{"type": "node_finished", "node": "a", "usage": a},
            {"type": "node_finished", "node": "b", "usage": b,
             "model_attempts": [{"attempt": 1, "provider": "openai", "model": "gpt-4o-mini", "status": "error", "code": "PROVIDER_RATE_LIMITED"},
                                {"attempt": 2, "provider": "ollama", "model": "llama3.2", "status": "ok"}]},
            {"type": "node_finished", "node": "r", "embedding_usage": emb("text-embedding-3-small", 5000, 0.0001)},
            {"type": "node_finished", "node": "c", "usage": {**make_usage("workflow", "child-wf", 9, 9), "provider": "workflow"}}]


def test_rows_add_up_to_the_run_totals():
    evs = three_node_events(); rows = run_usage.usage_rows(evs)
    by = {(r["node_id"], r["kind"], r["model"]): r for r in rows}
    assert set(by) == {("a", "llm", "gpt-4o"), ("b", "llm", "llama3.2"), ("b", "llm", "gpt-4o-mini"), ("r", "embedding", "text-embedding-3-small")}
    assert by[("b", "llm", "gpt-4o-mini")]["errors"] == 1 and by[("b", "llm", "gpt-4o-mini")]["calls"] == 0
    assert by[("b", "llm", "llama3.2")]["cost_usd"] is None and by[("a", "llm", "gpt-4o")]["duration_ms"] == 120.0
    m = summarize(evs, 0.0, 1.0)
    assert sum(r["tokens_in"] for r in rows) == m["tokens_in"] and sum(r["tokens_out"] for r in rows) == m["tokens_out"]
    priced = [r for r in rows if r["kind"] == "llm" and r["calls"]]
    assert any(r["cost_usd"] is None for r in priced) and m["cost_usd"] is None  # an unpriced chat model: the run's cost is unknown


def record(svc, rid, events, status="ok", uid="u1"):
    return svc.record(rid, "wf1", {}, events, {}, status, time.time() - 1, uid)


def test_written_once_at_run_end_and_replaced_on_refinish(db):
    svc = RunService(None, RunRepository(db), usage=RunUsageRepository(db)); repo = RunUsageRepository(db)
    rid = uuid.uuid4().hex[:10]
    record(svc, rid, three_node_events()[:1], status="waiting")
    assert repo.for_run(rid) == []  # not finished yet
    record(svc, rid, three_node_events()); record(svc, rid, three_node_events())  # finish, then a recovered re-finish
    rows = repo.for_run(rid)
    assert len(rows) == 4 and {r.owner for r in rows} == {"u1"} and {r.workflow_id for r in rows} == {"wf1"}
    run = RunRepository(db).get(rid)
    assert sum(r.tokens_in for r in rows) == run.tokens_in and sum(r.tokens_out for r in rows) == run.tokens_out
    with db.session() as s: s.add(Workflow(id="wf1", name="W", data="{}", updated=1.0, owner="u1")); s.commit()
    RunRepository(db).delete_for_workflow("wf1")
    assert repo.for_run(rid) == []  # deleted with the run


def test_priced_rows_sum_to_the_run_cost(db):
    svc = RunService(None, RunRepository(db), usage=RunUsageRepository(db)); rid = uuid.uuid4().hex[:10]
    evs = [{"type": "node_finished", "node": "a", "usage": make_usage("openai", "gpt-4o", 1000, 100)},
           {"type": "node_finished", "node": "b", "usage": make_usage("openai", "gpt-4o-mini", 2000, 100)},
           {"type": "node_finished", "node": "r", "embedding_usage": emb("text-embedding-3-small", 10000, 0.0002)}]
    record(svc, rid, evs)
    rows = RunUsageRepository(db).for_run(rid); run = RunRepository(db).get(rid)
    assert len(rows) == 3 and sum(r.cost_usd for r in rows) == pytest.approx(run.cost_usd)


def test_unique_key_rejects_duplicates(db):
    from sqlalchemy.exc import IntegrityError
    with db.session() as s:
        for i in range(2): s.add(RunUsage(id=f"x{i}", run_id="r", workflow_id="w", node_id="a", kind="llm", model="m", provider="p", created=1.0))
        with pytest.raises(IntegrityError): s.commit()


def test_backfill_from_run_events(db):
    import json
    now = time.time()
    with db.session() as s:
        s.add(Run(id="old1", workflow_id="w", status="ok", started=now - 100, ended=now - 90, owner="u1", events=json.dumps(three_node_events())))
        s.add(Run(id="old2", workflow_id="w", status="ok", started=now - 80, ended=now - 70, owner="u1", events="[]"))
        s.add(Run(id="wait", workflow_id="w", status="waiting", started=now - 60, owner="u1", events=json.dumps(three_node_events())))
        s.commit()
    repo = RunUsageRepository(db)
    assert run_usage.backfill(repo, 30, batch=1) == {"runs": 2, "rows": 4}
    assert run_usage.backfill(repo, 30) == {"runs": 1, "rows": 0}  # the run without model usage is looked at again, never duplicated
    assert len(repo.for_run("old1")) == 4 and repo.for_run("wait") == []


def migrate_cfg(db):
    cfg = Config(); cfg.set_main_option("script_location", os.path.normpath(MIGRATIONS_DIR))
    cfg.set_main_option("sqlalchemy.url", db.url.replace("%", "%%")); return cfg


def test_migrations_upgrade_and_downgrade(db):
    cfg = migrate_cfg(db)
    insp = inspect(db.engine)
    assert set(c["name"] for c in insp.get_columns("run_usage")) == set(RunUsage.__table__.columns.keys())
    assert "ix_chat_messages_status_created" in {i["name"] for i in insp.get_indexes("chat_messages")}
    command.downgrade(cfg, "0059_usage_indexes")
    insp = inspect(db.engine)
    assert "run_usage" not in insp.get_table_names() and "ix_chat_messages_status_created" not in {i["name"] for i in insp.get_indexes("chat_messages")}
    command.upgrade(cfg, "head")
    assert "run_usage" in inspect(db.engine).get_table_names()


# ---- the Usage page ----

def seed_people(db, now):
    with db.session() as s:
        for uid, email in (("ua", "a@example.com"), ("ub", "b@example.com"), ("uc", "deleted-uc@deleted.invalid")):
            s.add(User(id=uid, email=email, active=True))
        s.add(Team(id="t1", name="Red", created=now, created_by="ua")); s.add(Team(id="t2", name="Blue", created=now, created_by="ua"))
        for tid, uid in (("t1", "ua"), ("t1", "ub"), ("t2", "ub")): s.add(TeamMember(team_id=tid, user_id=uid, added=now))
        for rid, owner, tin, cost in (("ra", "ua", 100, 0.5), ("rb1", "ub", 10, 0.1), ("rb2", "ub", 10, None), ("rc", "uc", 1, 0.0)):
            s.add(Run(id=rid, workflow_id="w", status="ok", started=now - 60, ended=now - 30, owner=owner, events="[]", tokens_in=tin, tokens_out=1, cost_usd=cost))
        s.commit()
    repo = RunUsageRepository(db)
    repo.replace("ra", "w", "ua", now - 30, run_usage.usage_rows([{"type": "node_finished", "node": "a", "usage": make_usage("openai", "gpt-4o", 100, 1)}]))
    repo.replace("rb1", "w", "ub", now - 30, run_usage.usage_rows([{"type": "node_finished", "node": "a", "usage": make_usage("openai", "gpt-4o-mini", 10, 1)}]))
    repo.replace("rb2", "w", "ub", now - 30, run_usage.usage_rows([{"type": "node_finished", "node": "a", "usage": make_usage("ollama", "llama3.2", 10, 1)}]))


def test_models_users_and_teams_blocks(db):
    now = time.time(); seed_people(db, now); svc = UsageService(UsageRepository(db))
    out = svc.summary("x", "24h", sort="cost"); UsageSummary.model_validate(out)
    models = {(m["model"], m["provider"]): m for m in out["models"]}
    assert set(models) == {("gpt-4o", "openai"), ("gpt-4o-mini", "openai"), ("llama3.2", "ollama")}
    assert models[("gpt-4o", "openai")]["tokens_in"] == 100 and models[("llama3.2", "ollama")]["unpriced_rows"] == 1
    assert out["models_since"] == pytest.approx(now - 30)
    users = {u["user_id"]: u for u in out["users"]}
    assert users["ua"]["cost_usd"] == pytest.approx(0.5) and users["ub"]["runs"] == 2 and users["ub"]["unpriced_runs"] == 1
    assert users["uc"]["deleted"] and users["uc"]["email"] is None and users["ua"]["email"] == "a@example.com"
    assert [u["user_id"] for u in out["users"]][0] == "ua"  # by cost
    teams = {t["name"]: t for t in out["teams"]}
    assert teams["Red"]["runs"] == 3 and teams["Red"]["members"] == 2 and teams["Blue"]["runs"] == 2
    assert teams["Red"]["tokens_in"] == 120 and out["teams_shared_members"] == 1  # ub counts toward both teams


def test_empty_database_has_no_model_rows(db):
    out = UsageService(UsageRepository(db)).summary("x", "7d")
    assert out["models"] == [] and out["models_since"] is None and out["users"] == [] and out["teams"] == []


def test_usage_api_needs_users_manage():
    c = TestClient(app)
    tok = c.post("/api/auth/register", json={"email": f"m{uuid.uuid4().hex[:8]}@example.com", "password": "secret12"}).json()["data"]["token"]
    assert c.get("/api/admin/usage", headers={"Authorization": f"Bearer {tok}"}).status_code == 403
    adm = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]
    d = c.get("/api/admin/usage?window=24h", headers={"Authorization": f"Bearer {adm}"}).json()["data"]
    assert {"models", "users", "teams", "teams_shared_members", "models_since"} <= set(d)
    h = c.get("/api/admin/usage/health?window=24h", headers={"Authorization": f"Bearer {adm}"}).json()["data"]
    UsageHealth.model_validate(h)


def test_no_metric_label_is_a_user_or_team_id():
    """Every `labels(...)` call in the app passes only allowed label names, and none of them names a person or a team."""
    assert not LABELS & {"user_id", "owner", "team_id", "team", "user", "email", "run_id"}
    bad = []
    for f in APP.rglob("*.py"):
        for node in ast.walk(ast.parse(f.read_text())):
            if isinstance(node, ast.Call) and getattr(node.func, "id", getattr(node.func, "attr", None)) == "labels":
                for kw in node.keywords:
                    if kw.arg is None or kw.arg not in LABELS: bad.append(f"{f.relative_to(APP)}:{node.lineno} {kw.arg}")
                    v = ast.unparse(kw.value)
                    if any(w in v for w in ("owner", "user", "team", "uid", "email", "run_id", "rid")): bad.append(f"{f.relative_to(APP)}:{node.lineno} {v}")
    assert not bad, bad


# ---- chat refusals ----

def test_chat_refusals_by_code_and_platform(db):
    now = time.time()
    with db.session() as s:
        for i, (status, code, kind) in enumerate([("refused", "CHAT_IDENTITY_UNKNOWN", "slack"), ("refused", "CHAT_IDENTITY_UNKNOWN", "slack"),
                                                  ("refused", "RATE_LIMITED", "telegram"), ("started", None, "slack"), ("queued", None, "slack")]):
            s.add(ChatMessage(id=f"m{i}", channel_id="c", key=f"k{i}", trigger_id="t", workflow_id="w", kind=kind, sender="x", text="",
                              ref="{}", status=status, code=code, created=now - 10))
        s.add(ChatMessage(id="old", channel_id="c", key="old", trigger_id="t", workflow_id="w", kind="slack", sender="x", text="", ref="{}",
                          status="refused", code="RATE_LIMITED", created=now - 9 * 86400))
        s.commit()
    h = UsageService(UsageRepository(db)).counts(now - 86400, now)["channels"]
    assert h["refused"] == [{"code": "CHAT_IDENTITY_UNKNOWN", "kind": "slack", "count": 2}, {"code": "RATE_LIMITED", "kind": "telegram", "count": 1}]
    assert h["started"] == 1 and h["refused_total"] == 3 and h["refusal_share"] == 0.75


def test_refusal_query_uses_the_status_created_index(db):
    from sqlalchemy import func
    q = select(ChatMessage.code, ChatMessage.kind, func.count()).where(ChatMessage.status == "refused", ChatMessage.created >= 0.0,
                                                                        ChatMessage.created < 1e12).group_by(ChatMessage.code, ChatMessage.kind)
    sql = str(q.compile(db.engine, compile_kwargs={"literal_binds": True}))
    with db.engine.connect() as conn:
        plan = " ".join(str(r[-1]) for r in conn.exec_driver_sql("EXPLAIN QUERY PLAN " + sql).all())
    assert "ix_chat_messages_status_created" in plan, plan
