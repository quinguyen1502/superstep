"""Agent hand-off targets and the run limit (TASK-0179, REQ-0078, DEC-0073 decision 1)."""
import uuid
from fastapi.testclient import TestClient
from app.engine.validator import validate
from app.main import app

STATE = [{"name": "message", "type": "string"}, {"name": "answer", "type": "string"}]
TOOL = {"name": "lookup_order", "description": "Find an order", "source": "builtin", "function": "lookup_order"}


def agent(nid, label, handoffs=None, x=300):
    d = {"label": label, "prompt": "{{state.message}}", "output_field": "answer", "tools": [TOOL]}
    if handoffs is not None: d["handoffs"] = handoffs
    return {"id": nid, "type": "agent", "position": {"x": x, "y": 0}, "data": d}


def desk(handoffs=None, **top):
    """Triage → end, with Billing and Technical reached only by hand-off."""
    hs = [{"target": "billing", "description": "Charges and refunds"}, {"target": "tech", "description": "Bugs"}] if handoffs is None else handoffs
    return {"name": "desk", "state": STATE, **top,
            "nodes": [{"id": "s", "type": "start", "data": {}}, agent("triage", "Triage", hs), agent("billing", "Billing"),
                      agent("tech", "Technical"), {"id": "e", "type": "end", "data": {}}],
            "edges": [{"id": "1", "source": "s", "target": "triage"}, {"id": "2", "source": "triage", "target": "e"},
                      {"id": "3", "source": "billing", "target": "e"}, {"id": "4", "source": "tech", "target": "e"}]}


def codes(wf): return [getattr(i, "code", None) for i in validate(wf)]


def test_targets_make_agents_reachable_and_valid():
    assert validate(desk()) == []


def test_bad_targets_are_issues():
    for bad in ([{"target": "triage"}], [{"target": "s"}], [{"target": "nope"}], [{"target": "billing"}, {"target": "billing"}], "billing"):
        assert "AGENT_HANDOFF_TARGET_INVALID" in codes(desk(bad)), bad


def test_max_handoffs_range():
    assert validate(desk(max_handoffs=0)) == [] and validate(desk(max_handoffs=20)) == []
    for v in (-1, 21, "5", True):
        assert "AGENT_HANDOFF_LIMIT" in codes(desk(max_handoffs=v)), v


def test_workflows_without_the_fields_are_unchanged():
    wf = desk([]); wf["nodes"] = [n for n in wf["nodes"] if n["id"] not in ("billing", "tech")]; wf["edges"] = wf["edges"][:2]
    wf["nodes"][1]["data"].pop("handoffs")
    assert validate(wf) == []


def test_save_refuses_a_bad_target_with_a_translated_code():
    with TestClient(app) as c:
        tok = c.post("/api/auth/register", json={"email": f"h{uuid.uuid4().hex[:8]}@example.com", "password": "secret12"}).json()["data"]["token"]
        H = {"Authorization": f"Bearer {tok}"}
        r = c.post("/api/workflows", json=desk([{"target": "ghost"}]), headers=H)
        assert r.status_code == 400 and r.json()["error"]["code"] == "AGENT_HANDOFF_TARGET_INVALID"
        assert r.json()["error"]["details"]["target"] == "ghost"
        r = c.post("/api/workflows", json=desk(max_handoffs=50), headers=H)
        assert r.json()["error"]["code"] == "AGENT_HANDOFF_LIMIT"
        ok = c.post("/api/workflows", json=desk(max_handoffs=3), headers=H)
        assert ok.status_code == 200 and ok.json()["data"]["errors"] == []
        assert c.get(f"/api/workflows/{ok.json()['data']['id']}", headers=H).json()["data"]["max_handoffs"] == 3
