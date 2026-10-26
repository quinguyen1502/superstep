"""TASK-0132 (DEC-0065): validation messages carry a code, the API sends the codes, and the locales follow MESSAGES."""
import json, pathlib, re, string
from fastapi.testclient import TestClient
from app.engine import subgraphs
from app.engine.issues import INNER, MESSAGES, Issue, at_node, issues_of
from app.engine.validator import validate
from app.main import app
from app.services.run_service import error_event

ROOT = pathlib.Path(__file__).resolve().parents[2]
ENGINE = ROOT / "backend" / "app" / "engine"
c = TestClient(app)


def locale(lang):
    return json.loads((ROOT / "frontend" / "src" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))["validation"]


def i18next(template):
    return "".join(lit + (f"{{{{{f}}}}}" if f is not None else "") for lit, f, _, _ in string.Formatter().parse(template))


def test_locales_follow_the_english_messages():
    assert locale("en") == {k: i18next(v) for k, v in MESSAGES.items()}
    assert list(locale("vi")) == list(MESSAGES)


def test_every_code_in_the_engine_has_a_message():
    used = set()
    for path in ENGINE.glob("*.py"):
        used |= set(re.findall(r'Issue\("([A-Z_]+)"', path.read_text(encoding="utf-8")))
    assert used and used <= set(MESSAGES) | set(INNER), used - set(MESSAGES) - set(INNER)
    # built with f-strings in validator.py and foreach.py
    dynamic = {"DUPLICATE_NODE_ID", "DUPLICATE_EDGE_ID", "FOREACH_LIST_MISSING", "FOREACH_ITEM_MISSING",
               *(f"FOREACH_{w}_UNKNOWN" for w in ("LIST", "ITEM", "INDEX")), "FOREACH_LIST_TYPE", "FOREACH_INDEX_TYPE",
               "FOREACH_ITEM_REDUCER", "FOREACH_INDEX_REDUCER"}
    assert dynamic <= set(MESSAGES)


def test_an_issue_is_its_english_text():
    e = Issue("RETRIEVER_KB_MISSING", node="r1")
    assert e == "Retriever node r1: choose a knowledge base" and isinstance(e, str)
    assert e.to_dict() == {"code": "RETRIEVER_KB_MISSING", "params": {"node": "r1"}}
    assert Issue("INPUT_NOT_OBJECT") == 'Input must be a JSON object, e.g. {"message": "hi"}'
    # a code checker's own words keep their text and get the generic code
    assert at_node("c", "SyntaxError: invalid syntax (line 1)").to_dict() == \
        {"code": "NODE_PROBLEM", "params": {"node": "c", "detail": "SyntaxError: invalid syntax (line 1)"}}
    assert at_node("c", Issue("CODE_EMPTY")) == "Node c: the code is empty"
    assert issues_of(["plain", e]) == [None, e.to_dict()]


BROKEN = {"state": [{"name": "out", "type": "string"}, {"name": "loop:x", "type": "string"}],
          "nodes": [{"id": "s", "type": "start", "data": {}},
                    {"id": "r", "type": "retriever", "data": {"query": "{{state.nope | upper}}", "output_field": "out"}},
                    {"id": "a", "type": "agent", "data": {"prompt": "", "output_field": "out", "tools": [
                        {"name": "kb", "source": "knowledge"}, {"name": "kb", "source": "http", "method": "GET"}]}},
                    {"id": "e", "type": "end", "data": {}}],
          "edges": [{"id": "1", "source": "s", "target": "r"}, {"id": "2", "source": "r", "target": "a"},
                    {"id": "3", "source": "a", "target": "e"}]}


def test_every_message_of_a_broken_workflow_has_a_code():
    errs = validate(BROKEN)
    codes = [e.code for e in errs]
    assert all(isinstance(e, Issue) for e in errs), [e for e in errs if not isinstance(e, Issue)]
    for code in ("FIELD_RESERVED_FOREACH", "RETRIEVER_KB_MISSING", "VARIABLE_UNKNOWN", "AGENT_PROMPT_MISSING",
                 "AGENT_TOOL_KB", "AGENT_TOOL_DUPLICATE", "AGENT_TOOL_URL"):
        assert code in codes, (code, errs)
    assert "Agent node a: tool kb: choose a knowledge base" in errs  # the English text did not change


def test_subgraph_labels_reach_the_parameters():
    named = subgraphs.readable([Issue("RETRIEVER_KB_MISSING", node="sub/r"), "Node sub/r: plain"],
                               {"nodes": [{"id": "sub/r", "data": {"label": "Sub › Find"}}]})
    assert named == ['Retriever node "Sub › Find": choose a knowledge base', 'Node "Sub › Find": plain']
    assert named[0].params == {"node": '"Sub › Find"'} and not isinstance(named[1], Issue)


def tok(): return c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]


def test_the_api_sends_codes_next_to_the_messages():
    h = {"Authorization": f"Bearer {tok()}"}
    v = c.post("/api/validate", json=BROKEN, headers=h).json()["data"]
    assert len(v["issues"]) == len(v["errors"]) and v["issues"][0]["code"] == "FIELD_RESERVED_FOREACH"
    assert {"code": "RETRIEVER_KB_MISSING", "params": {"node": "r"}} in v["issues"]
    saved = c.post("/api/workflows", json={**BROKEN, "name": "Codes"}, headers=h).json()["data"]
    assert saved["errors"] == v["errors"] and saved["issues"] == v["issues"]
    made = c.post("/api/templates/builtin-rag/use", json={}, headers=h).json()["data"]
    assert made["issues"] == [{"code": "RETRIEVER_KB_MISSING", "params": {"node": "retrieve"}}]


def test_a_run_error_event_carries_the_codes():
    ev = error_event({"code": "WORKFLOW_INVALID", "message": "Workflow is invalid", "details": [Issue("END_MISSING")]})
    assert ev["errors"] == ["At least one End node is required"] and ev["issues"] == [{"code": "END_MISSING", "params": {}}]
    assert "issues" not in error_event({"code": "RUN_FAILED", "message": "boom"})
