"""Service unit tests with in-memory fake repositories (no DB, no HTTP)."""
import asyncio, json
from types import SimpleNamespace as NS
import pytest
from app.core.errors import AppError
from app.services.auth_service import AuthService
from app.services.run_service import RunService
from app.services.workflow_service import WorkflowService


class FakeWorkflows:
    def __init__(self): self.rows = {}
    def list_for_owner(self, o): return sorted([r for r in self.rows.values() if r.owner == o], key=lambda r: -r.updated)
    def get(self, wid): return self.rows.get(wid)
    def referencing(self, wid): return [r for r in self.rows.values() if r.id != wid and f'"{wid}"' in (r.data or "")]
    def get_owned(self, wid, o): r = self.rows.get(wid); return r if r and r.owner == o else None
    def names_for_owner(self, o, exclude=None): return {r.name for r in self.rows.values() if r.owner == o and r.id != exclude}
    def save(self, wid, name, data, updated, owner): self.rows[wid] = NS(id=wid, name=name, data=data, updated=updated, owner=owner)
    def update_name(self, wid, name, data, updated): self.rows[wid].__dict__.update(name=name, data=data, updated=updated)
    def delete(self, wid): self.rows.pop(wid, None)
    def exists(self, wid): return wid in self.rows
    def adopt_unowned(self, o): pass

class FakeRuns:
    def __init__(self): self.rows = []
    def add(self, r):
        # Match RunRepository.add's upsert contract: live snapshots and the final
        # record update one run, not several independent rows.
        self.rows = [row for row in self.rows if row.id != r.id] + [r]
    def last_for_workflow(self, wid): rs = [r for r in self.rows if r.workflow_id == wid]; return max(rs, key=lambda r: r.started) if rs else None
    def list_for_workflow(self, wid, limit=50, tests=False): return [r for r in self.rows if r.workflow_id == wid and (r.source == "test") == tests][:limit]
    def delete_for_workflow(self, wid): self.rows = [r for r in self.rows if r.workflow_id != wid]

class FakeUsers:
    def __init__(self): self.rows = {}
    def get_by_email(self, e): return self.rows.get(e)
    def add(self, uid, email, pw, created): self.rows[email] = NS(id=uid, email=email, password=pw, created=created, role="editor", active=True)
    def get_by_id(self, uid): return next((u for u in self.rows.values() if u.id == uid), None)
    def set_role(self, uid, role): self.get_by_id(uid).role = role


@pytest.fixture
def svc():
    wf, runs = FakeWorkflows(), FakeRuns()
    return NS(wf=wf, runs=runs, workflows=WorkflowService(wf, runs), runner=RunService(wf, runs))


def test_workflow_crud_naming_and_ownership(svc):
    s = svc.workflows
    a = s.save({"name": "  Flow   A ", "nodes": [], "edges": []}, "u1")
    b = s.save({"name": "Flow A"}, "u1")
    assert s.get(a["id"], "u1")["name"] == "Flow A" and s.get(b["id"], "u1")["name"] == "Flow A (copy)"
    with pytest.raises(AppError): s.get(a["id"], "u2")
    with pytest.raises(AppError): s.save({"id": a["id"], "name": "x"}, "u2")
    with pytest.raises(AppError): s.rename(b["id"], "Flow A", "u1")
    with pytest.raises(AppError): s.rename(b["id"], "   ", "u1")
    assert s.duplicate(a["id"], "u1")["name"] == "Flow A (copy 2)"
    s.delete(a["id"], "u1"); assert len(s.list("u1")) == 2


def test_save_keeps_server_source_and_ignores_client_source(svc):
    svc.wf.save("imp", "Imp", json.dumps({"name": "Imp", "source": {"kind": "langgraph_import"}}), 1, "u1")
    out = svc.workflows.save({"id": "imp", "name": "Imp", "source": {"kind": "evil"}}, "u1")
    assert out["errors"] == [] and json.loads(svc.wf.rows["imp"].data)["source"]["kind"] == "langgraph_import"
    fresh = svc.workflows.save({"name": "N", "source": {"kind": "langgraph_import"}}, "u1")
    assert "source" not in json.loads(svc.wf.rows[fresh["id"]].data)


def test_list_includes_last_run(svc):
    wid = svc.workflows.seed_example("u1")
    svc.runner.record("r1", wid, {}, [{"type": "run_started"}], {"x": 1}, "ok", 5.0)
    [row] = svc.workflows.list("u1")
    assert row["last_run_status"] == "ok" and row["last_run_at"] == 5.0 and row["node_count"] > 0
    assert svc.runner.history(wid, "u1")[0]["final_state"] == {"x": 1}
    with pytest.raises(AppError): svc.runner.history(wid, "u2")


def test_auth_register_login(svc):
    users = FakeUsers(); a = AuthService(users, svc.workflows)
    out = a.register(" Bob@Example.com ", "abc12345")
    assert out["user"]["email"] == "bob@example.com" and svc.workflows.list(out["user"]["id"])  # example seeded
    with pytest.raises(AppError): a.register("bob@example.com", "abc12345")
    with pytest.raises(AppError): a.register("nope", "abc12345")
    with pytest.raises(AppError): a.register("c@d.ef", "short")
    assert AuthService.user_from_token(a.login("BOB@example.com", "abc12345")["token"])["email"] == "bob@example.com"
    with pytest.raises(AppError): a.login("bob@example.com", "wrong999")
    with pytest.raises(AppError): AuthService.user_from_token(None)


def test_run_plan_rejections(svc):
    p = svc.runner.plan
    with pytest.raises(AppError): p("u1", [1])
    with pytest.raises(AppError): p("u1", {"workflow_id": "missing"})
    with pytest.raises(AppError): p("u1", {"input": "x"})
    with pytest.raises(AppError): p("u1", {"workflow": "x"})


def test_run_execute_records_history(svc):
    wid = svc.workflows.seed_example("u1")
    plan = svc.runner.plan("u1", {"workflow_id": wid, "input": {"message": "where is my order 123"}})
    sent = []
    async def send(ev): sent.append(ev); return True
    async def listen(): await asyncio.sleep(3600)
    assert asyncio.run(svc.runner.execute(plan, send, listen)) == "ok"
    assert sent[0]["type"] == "run_started" and sent[-2]["type"] == "run_finished"
    summary = sent[-1]; assert summary["type"] == "run_summary" and summary["status"] == "ok"
    m = summary["metrics"]; assert m["tokens"] > 0 and m["cost_usd"] == 0.0 and m["error_count"] == 0  # mock: estimated tokens, free
    assert summary["trace_id"] is None and summary["trace_url"] is None  # no exporter -> no trace
    [r] = svc.runs.rows; assert r.status == "ok" and r.workflow_id == wid and r.tokens_in == m["tokens_in"] and r.duration_ms > 0


def test_run_execute_cancel(svc):
    plan = svc.runner.plan("u1", {"workflow": {"name": "x"}, "input": {}})
    async def send(ev): return True
    async def listen(): return "cancelled"
    status = asyncio.run(svc.runner.execute(plan, send, listen))
    assert status in ("cancelled", "error") and svc.runs.rows[0].workflow_id == "adhoc"


# ---- credentials (TASK-0005) ----
from app.core import crypto
from app.services.credential_service import CredentialService


class FakeCredentials:
    def __init__(self): self.rows = {}
    def add(self, c): self.rows[c.id] = c; return c
    def list_for_owner(self, o): return sorted([c for c in self.rows.values() if c.owner == o], key=lambda c: -c.created)
    def get_owned(self, cid, o): c = self.rows.get(cid); return c if c and c.owner == o else None
    def delete_owned(self, cid, o):
        if self.get_owned(cid, o): del self.rows[cid]; return True
        return False


def test_credential_service_encrypts_and_masks():
    repo = FakeCredentials(); s = CredentialService(repo)
    out = s.create("u1", " oai ", "openai", " sk-abcdef123456 ", None)
    stored = repo.rows[out["id"]]
    assert "sk-abcdef123456" not in stored.secret and crypto.decrypt(stored.secret) == "sk-abcdef123456"
    assert out["hint"] == "••••3456" and out["name"] == "oai" and "secret" not in out
    assert s.list("u1") == [out] and s.list("u2") == []


def test_credential_service_rejections_and_ownership():
    s = CredentialService(FakeCredentials())
    with pytest.raises(AppError): s.create("u1", "x", "nope", "k", None)
    with pytest.raises(AppError): s.create("u1", "x", "openai", "  ", None)
    with pytest.raises(AppError): s.create("u1", "x", "openai", "k", "ftp://x")
    cid = s.create("u1", "", "anthropic", "sk-ant-123456789", None)["id"]
    r = s.resolver("u1")(cid)
    assert r["api_key"] == "sk-ant-123456789" and r["base_url"] == "https://api.anthropic.com" and r["name"] == "anthropic"
    with pytest.raises(AppError, match="not yours"): s.resolver("u2")(cid)
    with pytest.raises(AppError): s.delete(cid, "u2")
    assert s.delete(cid, "u1") == {"ok": True}


def test_run_plan_carries_user_bound_resolver(svc):
    repo = FakeCredentials(); creds = CredentialService(repo)
    cid = creds.create("u1", "k", "openai", "sk-0123456789", "https://llm.example/v1")["id"]
    runner = RunService(svc.wf, svc.runs, creds)
    plan = runner.plan("u1", {"workflow": {"name": "x"}, "input": {}})
    assert plan.resolve(cid)["base_url"] == "https://llm.example/v1"
    assert RunService(svc.wf, svc.runs).plan("u1", {"workflow": {}, "input": {}}).resolve is None
