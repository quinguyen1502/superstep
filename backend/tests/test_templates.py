"""TASK-0025: template library: built-ins, save-as (sanitised), import/export, use, scopes, delete."""
import json, uuid
from pathlib import Path
import pytest
from types import SimpleNamespace as NS
from fastapi.testclient import TestClient
from app.engine import templates as T
from app.engine.runtime import run_stream
from app.engine.validator import validate
from app.main import app

c = TestClient(app)
H = lambda t: {"Authorization": f"Bearer {t}"}
code = lambda r: r.json()["error"]["code"]


def register():
    email = f"t{uuid.uuid4().hex[:6]}@example.com"
    d = c.post("/api/auth/register", json={"email": email, "password": "secret12"}).json()["data"]
    return NS(token=d["token"], id=d["user"]["id"])


def admin():
    return NS(token=c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"])


SECRETY = {"name": "Secrety", "state": [{"name": "message", "type": "string"}, {"name": "out", "type": "string"}],
           "nodes": [{"id": "start", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "Start"}},
                     {"id": "call", "type": "tool", "position": {"x": 200, "y": 0},
                      "data": {"label": "Call", "mode": "http", "url": "https://x.example", "credential_id": "cred-1",
                               "headers": {"Authorization": "Bearer abc"}, "api_key": "sk-1", "_status": "ok", "output_field": "out"}},
                     {"id": "end", "type": "end", "position": {"x": 400, "y": 0}, "data": {"label": "End"}}],
           "edges": [{"id": "e1", "source": "start", "target": "call"}, {"id": "e2", "source": "call", "target": "end"}]}


def test_sanitize_strips_refs_secrets_and_runtime():
    g = T.sanitize(SECRETY)
    d = g["nodes"][1]["data"]
    assert d["credential_id"] == "" and "headers" not in d and "api_key" not in d and "_status" not in d
    assert d["url"] == "https://x.example" and "name" not in g and SECRETY["nodes"][1]["data"]["api_key"] == "sk-1"  # input untouched


def test_builtins_are_well_formed():
    for b in T.BUILTINS:
        assert T.problems(T.export_payload(b["name"], b["description"], b["workflow"])) == []
        # only "pick your KB" may remain, and a workflow tool's workflow, which a helper fills in when used (TASK-0137)
        assert all("knowledge base" in e or (b.get("helpers") and "choose a workflow" in e) for e in validate(b["workflow"]))


def test_builtins_have_a_name_and_description_in_both_ui_languages():
    """The gallery shows built-ins by `templates.builtin.<id>` (TASK-0120 adds the Support agent's)."""
    for lang in ("en", "vi"):
        shown = json.loads((Path(__file__).resolve().parents[2] / f"frontend/src/locales/{lang}.json").read_text())["templates"]["builtin"]
        assert sorted(shown) == sorted(b["id"] for b in T.BUILTINS), lang
        assert all(shown[b["id"]].get("name") and shown[b["id"]].get("description") for b in T.BUILTINS), lang


NEW = ["builtin-refund-approval", "builtin-leave-request", "builtin-social-post", "builtin-large-order", "builtin-expense-claim",
       "builtin-purchase-request", "builtin-support-escalation", "builtin-feedback-digest", "builtin-support-agent", "builtin-support-team"]
FIRST_HUMAN = {"builtin-refund-approval": "finance", "builtin-leave-request": "manager", "builtin-social-post": "editor",
               "builtin-large-order": "manager", "builtin-expense-claim": "approver", "builtin-purchase-request": "lead"}
INPUTS = {"request": "Refund order 1042, $80, the parcel arrived broken.", "message": "I'd like leave from 3 to 5 March for a family event.",
          "brief": "Launch of our new dark mode", "order": "Order 77: 40 laptops, new customer, delivery to a new address",
          "claim": "Hotel $180 x 2 nights, meals $40", "customer_email": "ann@example.com", "employee_email": "bo@example.com",
          "requester_email": "cy@example.com", "feedback": ["Love the new editor", "Runs are slow on Mondays", "Please add a Discord channel"]}


def test_builtin_order_and_channel_kinds():
    """TASK-0064: the built-ins, the new ones after the first four (TASK-0119 adds the Support agent, TASK-0137 the Support team). Human nodes on a channel store only its kind."""
    assert [b["id"] for b in T.BUILTINS] == ["builtin-chatbot", "builtin-rag", "builtin-approval", "builtin-router", *NEW]
    kinds = {b["id"]: [n["data"]["approval"] for n in b["workflow"]["nodes"] if n["type"] == "human" and "approval" in n["data"]] for b in T.BUILTINS}
    assert {i: [a["channel"] for a in v] for i, v in kinds.items() if v} == {
        "builtin-refund-approval": ["slack"], "builtin-leave-request": ["teams"], "builtin-social-post": ["telegram"],
        "builtin-large-order": ["whatsapp"], "builtin-expense-claim": ["email"], "builtin-purchase-request": ["slack", "email"]}
    assert all(list(a) == ["channel"] for v in kinds.values() for a in v)


def test_channel_templates_have_deadlines():
    """TASK-0066: every Human node on a channel has a deadline that suits the process; only the social post approves on timeout."""
    from app.engine import deadlines
    due = {(b["id"], n["id"]): deadlines.parse(n["data"]) for b in T.BUILTINS for n in b["workflow"]["nodes"] if n["type"] == "human" and n["data"].get("approval")}
    assert len(due) == 7 and all(due.values())
    assert {k for k, v in due.items() if v["on_timeout"] == "approve"} == {("builtin-social-post", "editor")}
    assert due[("builtin-leave-request", "manager")] == {"after": 172800.0, "remind_every": 86400.0, "on_timeout": "reject", "escalate_to": []}


@pytest.mark.parametrize("tid", [i for i in NEW if i not in ("builtin-support-escalation", "builtin-support-agent", "builtin-support-team")])
# those need a knowledge base, like builtin-rag, or child runs (test_workflow_tool_template.py)
def test_new_builtins_run_offline(tid, monkeypatch):
    """Mock LLM and dry-run e-mail: each runs up to its first Human node, or to the end."""
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "TYPESAFE_API_KEY"): monkeypatch.delenv(k, raising=False)
    wf = next(b for b in T.BUILTINS if b["id"] == tid)["workflow"]
    evs = list(run_stream(wf, {k: v for k, v in INPUTS.items() if any(f["name"] == k for f in wf["state"])}))
    assert not [e for e in evs if e["type"] == "error"]
    if tid in FIRST_HUMAN: assert evs[-1]["type"] == "run_waiting" and evs[-1]["node"] == FIRST_HUMAN[tid]
    else: assert evs[-1]["type"] == "run_finished" and len(evs[-1]["state"]["labelled"]) == 3 and evs[-1]["state"]["report"] and evs[-1]["state"]["sent"]


def test_channel_template_waits_in_the_studio_without_a_connection():
    """A workflow made from a channel template keeps the kind and, with no connection yet, waits to be approved in the studio."""
    u = register(); wid = c.post("/api/templates/builtin-refund-approval/use", headers=H(u.token), json={}).json()["data"]["id"]
    wf = c.get(f"/api/workflows/{wid}", headers=H(u.token)).json()["data"]
    assert next(n for n in wf["nodes"] if n["id"] == "finance")["data"]["approval"] == {"channel": "slack"}
    with c.websocket_connect(f"/ws/run?token={u.token}") as ws:
        ws.send_json({"workflow_id": wid, "input": {"request": "Refund order 1042", "customer_email": "ann@example.com"}}); evs = []
        while not evs or evs[-1]["type"] not in ("run_finished", "run_waiting", "error"): evs.append(ws.receive_json())
    assert evs[-1]["type"] == "run_waiting" and evs[-1]["node"] == "finance"


def test_sanitize_blanks_the_resources_of_agent_tools():
    """TASK-0119: an Agent node's tools point at knowledge bases and MCP servers too; secret-like keys go as well."""
    wf = {"nodes": [{"id": "ag", "type": "agent", "data": {"credential_id": "c1", "tools": [
        {"name": "kb", "source": "knowledge", "knowledge_base_id": "kb-1", "top_k": 3},
        {"name": "m", "source": "mcp", "server_id": "srv-1", "tool": "add", "api_key": "sk-1"}, "odd"]}}]}
    tools = T.sanitize(wf)["nodes"][0]["data"]["tools"]
    assert tools == [{"name": "kb", "source": "knowledge", "knowledge_base_id": "", "top_k": 3}, {"name": "m", "source": "mcp", "server_id": "", "tool": "add"}, "odd"]
    assert wf["nodes"][0]["data"]["tools"][0]["knowledge_base_id"] == "kb-1"  # the input is not changed


def test_sanitize_keeps_only_the_channel_kind():
    """Saved and exported templates drop a Human node's connection, target and approvers (TASK-0064)."""
    wf = {"nodes": [{"id": "a", "type": "human", "data": {"approval": {"channel_id": "c1", "channel": "slack", "target": "C1", "approvers": ["x@y.z"]}}},
                    {"id": "b", "type": "human", "data": {"approval": {"channel_id": "c2"}}}], "edges": []}
    assert [n["data"]["approval"] for n in T.sanitize(wf)["nodes"]] == [{"channel": "slack"}, {}]


def test_problems():
    assert T.problems([]) == ["not a JSON object"]
    bad = {"format": T.FORMAT, "version": 1, "workflow": {"nodes": [{"id": "a", "type": "llm"}], "edges": [{"source": "a", "target": "zz"}]}}
    errs = T.problems(bad)
    assert any("Start" in e for e in errs) and any("edge" in e for e in errs)
    assert T.problems({"format": "x", "version": 2, "workflow": {}})[:2] == ["format must be 'superstep/template'", "unsupported version 2"]


def test_list_use_builtin():
    u = register()
    ts = c.get("/api/templates", headers=H(u.token)).json()["data"]
    assert [t["id"] for t in ts[:4]] == ["builtin-chatbot", "builtin-rag", "builtin-approval", "builtin-router"]
    assert ts[0]["nodes"] and "data" not in ts[0]["nodes"][0]  # preview only
    r = c.post("/api/templates/builtin-chatbot/use", headers=H(u.token), json={}).json()["data"]
    r2 = c.post("/api/templates/builtin-chatbot/use", headers=H(u.token)).json()["data"]
    names = {w["id"]: w["name"] for w in c.get("/api/workflows", headers=H(u.token)).json()["data"]}
    assert names[r["id"]] == "Chatbot" and names[r2["id"]] != "Chatbot" and r["errors"] == []
    assert code(c.post("/api/templates/nope/use", headers=H(u.token))) == "TEMPLATE_NOT_FOUND"


def test_save_as_export_import_delete():
    u, other = register(), register()
    wid = c.post("/api/workflows", headers=H(u.token), json=SECRETY).json()["data"]["id"]
    t = c.post("/api/templates", headers=H(u.token), json={"workflow_id": wid, "name": "  My  tpl ", "description": "d"}).json()["data"]
    assert t["name"] == "My tpl" and t["scope"] == "user" and t["mine"] and t["deletable"]
    exp = c.get(f"/api/templates/{t['id']}/export", headers=H(u.token)).json()["data"]
    assert exp["format"] == T.FORMAT and "sk-1" not in str(exp) and "cred-1" not in str(exp)
    # private: other users can't see, export, use or delete it
    assert t["id"] not in [x["id"] for x in c.get("/api/templates", headers=H(other.token)).json()["data"]]
    for r in (c.get(f"/api/templates/{t['id']}/export", headers=H(other.token)), c.delete(f"/api/templates/{t['id']}", headers=H(other.token))):
        assert code(r) == "TEMPLATE_NOT_FOUND"
    # other can't save someone else's workflow as a template
    assert c.post("/api/templates", headers=H(other.token), json={"workflow_id": wid, "name": "x"}).status_code in (403, 404)
    imp = c.post("/api/templates/import", headers=H(other.token), json={"file": exp}).json()["data"]
    assert imp["name"] == "My tpl" and imp["mine"]
    bad = c.post("/api/templates/import", headers=H(other.token), json={"file": {"format": "nope"}})
    assert code(bad) == "TEMPLATE_INVALID" and bad.json()["error"]["details"]
    assert code(c.post("/api/templates", headers=H(u.token), json={"workflow_id": wid, "name": "  "})) == "TEMPLATE_NAME_REQUIRED"
    assert code(c.delete("/api/templates/builtin-rag", headers=H(u.token))) == "TEMPLATE_READ_ONLY"
    assert c.delete(f"/api/templates/{t['id']}", headers=H(u.token)).json()["data"] == {"ok": True}
    assert code(c.delete(f"/api/templates/{t['id']}", headers=H(u.token))) == "TEMPLATE_NOT_FOUND"


def test_org_scope_needs_admin():
    u, a = register(), admin()
    wid = c.post("/api/workflows", headers=H(u.token), json=SECRETY).json()["data"]["id"]
    assert code(c.post("/api/templates", headers=H(u.token), json={"workflow_id": wid, "name": "Org", "scope": "org"})) == "TEMPLATE_SCOPE_FORBIDDEN"
    awid = c.post("/api/workflows", headers=H(a.token), json=SECRETY).json()["data"]["id"]
    t = c.post("/api/templates", headers=H(a.token), json={"workflow_id": awid, "name": "Org wide", "scope": "org"}).json()["data"]
    seen = {x["id"]: x for x in c.get("/api/templates", headers=H(u.token)).json()["data"]}
    assert seen[t["id"]]["scope"] == "org" and not seen[t["id"]]["deletable"]
    assert code(c.delete(f"/api/templates/{t['id']}", headers=H(u.token))) == "TEMPLATE_READ_ONLY"
    assert c.post(f"/api/templates/{t['id']}/use", headers=H(u.token)).json()["data"]["id"]
    assert c.delete(f"/api/templates/{t['id']}", headers=H(a.token)).json()["data"]["ok"]


def test_v010_format_still_imports():
    b = T.BUILTINS[0]
    old = {**T.export_payload(b["name"], b["description"], b["workflow"]), "format": "langgraph-studio/template"}
    assert T.problems(old) == [] and T.export_payload("x", None, b["workflow"])["format"] == "superstep/template"


# ---------- test cases of the built-in templates (TASK-0069) ----------
def test_builtin_test_cases_are_valid():
    from app.engine import checks
    for b in T.BUILTINS:
        assert 1 <= len(b["tests"]) <= 3, b["id"]
        nodes = {n["id"] for n in b["workflow"]["nodes"]}; fields = {f["name"] for f in b["workflow"]["state"]}
        for case in b["tests"]:
            assert checks.errors(case["checks"]) == [] and set(case["answers"]) <= nodes and set(case["input"]) <= fields, (b["id"], case["name"])
            assert all(ch.get("node", "start") in nodes and ch.get("field", "message") in fields | {"message"} for ch in case["checks"]), (b["id"], case["name"])


def test_builtin_test_cases_pass_in_mock_mode(monkeypatch):
    """Every built-in template, used as a workflow, runs its own cases offline and passes them all. The two knowledge base
    templates get a small FAQ first, as a user picks one."""
    from tests.test_workflow_tests import run_all
    for k in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "TYPESAFE_API_KEY"): monkeypatch.delenv(k, raising=False)
    with TestClient(app) as cl:  # the worker runs the test runs
        u = register(); h = H(u.token)
        kb = cl.post("/api/knowledge-bases", json={"name": "FAQ"}, headers=h).json()["data"]
        cl.post(f"/api/knowledge-bases/{kb['id']}/documents", files={"file": ("faq.txt", b"Laptops have a two-year warranty.")}, headers=h)
        for b in T.BUILTINS:
            wid = cl.post(f"/api/templates/{b['id']}/use", headers=h, json={}).json()["data"]["id"]
            cases = cl.get(f"/api/workflows/{wid}/tests", headers=h).json()["data"]["items"]
            assert [x["name"] for x in cases] == [x["name"] for x in b["tests"]], b["id"]
            wf = cl.get(f"/api/workflows/{wid}", headers=h).json()["data"]
            if any(n["type"] in ("retriever", "agent") for n in wf["nodes"]):
                for n in wf["nodes"]:
                    if n["type"] == "retriever": n["data"]["knowledge_base_id"] = kb["id"]
                    for t in n["data"].get("tools") or []:  # an Agent node's knowledge base tools (TASK-0119)
                        if t.get("source") == "knowledge": t["knowledge_base_id"] = kb["id"]
                cl.post("/api/workflows", json=wf, headers=h)
            suite = run_all(cl, {"token": u.token}, wid, mock=True)
            assert {r["name"]: (r["status"], r["reason"], [ch for ch in r["checks"] if ch["passed"] is False]) for r in suite["results"]} == \
                   {x["name"]: ("passed", None, []) for x in b["tests"]}, b["id"]


def test_saved_templates_carry_no_test_cases():
    u = register(); h = H(u.token)
    wid = c.post("/api/templates/builtin-leave-request/use", headers=h, json={}).json()["data"]["id"]
    assert len(c.get(f"/api/workflows/{wid}/tests", headers=h).json()["data"]["items"]) == 2
    tpl = c.post("/api/templates", json={"workflow_id": wid, "name": f"Mine {uuid.uuid4().hex[:4]}"}, headers=h).json()["data"]
    assert tpl["tests"] == 0 and "tests" not in c.get(f"/api/templates/{tpl['id']}/export", headers=h).json()["data"]
    again = c.post(f"/api/templates/{tpl['id']}/use", headers=h, json={}).json()["data"]["id"]
    assert c.get(f"/api/workflows/{again}/tests", headers=h).json()["data"]["items"] == []
    listed = {t["id"]: t["tests"] for t in c.get("/api/templates", headers=h).json()["data"]}
    assert listed["builtin-purchase-request"] == 3 and listed[tpl["id"]] == 0
