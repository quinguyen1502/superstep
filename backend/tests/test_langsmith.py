"""LangSmith (opt-in): a finished test suite goes to LangSmith as a dataset + experiment when the admin setting is on,
"Send to LangSmith" sends one again, and runs traced to LangSmith link to their LangSmith page. LangSmith is a fake."""
import time, types, uuid
import pytest
from app.services import langsmith as LS
from app.services.telemetry import trace_url
from tests.test_workflow_tests import APPROVAL, H, add, c, run_all, save, user  # noqa: F401 (fixture)


class Fake:
    """Records what a langsmith.Client would be asked to do."""
    _host_url = "https://smith.example.com"

    def __init__(self): self.datasets, self.examples, self.projects, self.runs, self.feedback, self.ended, self.fail = {}, {}, [], [], [], [], False

    def _obj(self, **kw): return types.SimpleNamespace(id=uuid.uuid4(), tenant_id="ten", **kw)
    def read_project(self, project_name): return types.SimpleNamespace(id="proj", tenant_id="ten", name=project_name)
    def list_datasets(self, dataset_name): return [d for d in self.datasets.values() if d.name == dataset_name]
    def create_dataset(self, name, **kw):
        if self.fail: raise ConnectionError("down")
        d = self._obj(name=name, **kw); self.datasets[d.id] = d; return d
    def list_examples(self, dataset_id): return [e for e in self.examples.values() if e.dataset_id == dataset_id]
    def create_example(self, dataset_id, inputs, outputs, metadata):
        e = self._obj(dataset_id=dataset_id, inputs=inputs, outputs=outputs, metadata=metadata); self.examples[e.id] = e; return e
    def update_example(self, eid, inputs, outputs, metadata): self.examples[eid].__dict__.update(inputs=inputs, outputs=outputs, metadata=metadata)
    def create_project(self, name, **kw): p = self._obj(name=name, **kw); self.projects.append(p); return p
    def create_run(self, name, inputs, run_type, **kw): self.runs.append({"name": name, "inputs": inputs, **kw})
    def create_feedback(self, rid, key, **kw): self.feedback.append((rid, key, kw["score"]))
    def update_project(self, pid, end_time): self.ended.append(pid)


@pytest.fixture
def fake(monkeypatch):
    f = Fake(); monkeypatch.setattr(LS, "client_factory", lambda: f); LS._project.clear()
    monkeypatch.setenv("LANGSMITH_API_KEY", "test-key"); return f


def admin(c):
    return {"token": c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]}


def setting(c, on):
    return c.put("/api/admin/langsmith", json={"evals": on}, headers=H(admin(c)["token"])).json()


def wait_url(c, u, wid, sid):
    t0 = time.time()
    while time.time() - t0 < 10:
        s = c.get(f"/api/workflows/{wid}/tests/runs/{sid}", headers=H(u["token"])).json()["data"]
        if s["langsmith_url"]: return s
        time.sleep(0.05)
    raise AssertionError("suite not sent")


def test_setting_is_admin_only_and_reports_configuration(c, fake, monkeypatch):
    u = user(c)
    assert c.get("/api/admin/langsmith", headers=H(u["token"])).json()["error"]["code"] == "PERMISSION_DENIED"
    assert c.put("/api/admin/langsmith", json={"evals": True}, headers=H(u["token"])).json()["error"]["code"] == "PERMISSION_DENIED"
    d = setting(c, True)["data"]
    assert d["configured"] and d["evals"] and d["project"] == "default" and "test-key" not in str(d)
    monkeypatch.delenv("LANGSMITH_API_KEY")
    assert c.get("/api/admin/langsmith", headers=H(admin(c)["token"])).json()["data"]["configured"] is False
    setting(c, False)


def test_finished_suite_becomes_a_dataset_and_experiment(c, fake):
    setting(c, True)
    try:
        u = user(c); wid = save(c, u, APPROVAL)
        add(c, u, wid, name="Approved", answers={"ask": ["approved"]}, checks=[{"kind": "field", "field": "decision", "op": "equals", "value": "approved"}])
        add(c, u, wid, name="Wrong", answers={"ask": ["rejected"]}, checks=[{"kind": "field", "field": "decision", "op": "equals", "value": "approved"}])
        lst = c.get(f"/api/workflows/{wid}/tests", headers=H(u["token"])).json()["data"]
        assert lst["langsmith"] is True and lst["langsmith_configured"] is True
        s = wait_url(c, u, wid, run_all(c, u, wid)["id"])
        (ds,) = fake.datasets.values(); (exp,) = fake.projects
        assert ds.name.endswith(f"({wid})") and exp.reference_dataset_id == ds.id and fake.ended == [exp.id]
        assert s["langsmith_url"] == f"https://smith.example.com/o/ten/datasets/{ds.id}/compare?selectedSessions={exp.id}"
        assert sorted(e.metadata["name"] for e in fake.examples.values()) == ["Approved", "Wrong"]
        assert {r["name"]: r["outputs"].get("decision") for r in fake.runs} == {"Approved": "approved", "Wrong": "rejected"}
        passed = {next(r["name"] for r in fake.runs if r["id"] == rid): sc for rid, k, sc in fake.feedback if k == "passed"}
        assert passed == {"Approved": 1.0, "Wrong": 0.0} and any(k.startswith("check 1") for _, k, _ in fake.feedback)
        # sending again: the same dataset and examples (kept in sync), a second experiment
        again = c.post(f"/api/workflows/{wid}/tests/runs/{s['id']}/langsmith", headers=H(u["token"])).json()["data"]
        assert len(fake.datasets) == 1 and len(fake.examples) == 2 and len(fake.projects) == 2 and again["langsmith_url"].endswith(str(fake.projects[1].id))
        fake.fail = True; fake.datasets.clear()
        r = c.post(f"/api/workflows/{wid}/tests/runs/{s['id']}/langsmith", headers=H(u["token"])).json()
        assert r["error"]["code"] == "LANGSMITH_PUSH_FAILED" and r["error"]["details"] == {"reason": "ConnectionError"}
        viewer = user(c)
        assert c.post(f"/api/workflows/{wid}/tests/runs/{s['id']}/langsmith", headers=H(viewer["token"])).json()["success"] is False
    finally:
        setting(c, False)


def test_off_or_unconfigured_sends_nothing(c, fake, monkeypatch):
    u = user(c); wid = save(c, u, APPROVAL); add(c, u, wid, answers={"ask": ["approved"]})
    s = run_all(c, u, wid); time.sleep(0.3)
    assert fake.projects == [] and s["langsmith_url"] is None
    monkeypatch.delenv("LANGSMITH_API_KEY")
    r = c.post(f"/api/workflows/{wid}/tests/runs/{s['id']}/langsmith", headers=H(u["token"])).json()
    assert r["error"]["code"] == "LANGSMITH_NOT_CONFIGURED"


def test_trace_link_to_langsmith(fake, monkeypatch):
    monkeypatch.delenv("STUDIO_TRACE_URL", raising=False)
    assert trace_url("t" * 32, "00000000000000ab") is None  # not tracing to LangSmith
    monkeypatch.setenv("LANGSMITH_TRACING", "true")
    rid = str(uuid.UUID(int=0xab))
    assert trace_url("t" * 32, "00000000000000ab") == f"https://smith.example.com/o/ten/projects/p/proj/r/{rid}?trace_id={rid}"
    assert trace_url("t" * 32, None) is None and trace_url(None, "ab") is None
    monkeypatch.setenv("STUDIO_TRACE_URL", "http://j/trace/{trace_id}")
    assert trace_url("abc", "ab") == "http://j/trace/abc"  # an explicit viewer wins
