"""TASK-0070 (REQ-0043, DEC-0045): export a workflow as a readable, runnable LangGraph Python file.

The exported file runs in a separate Python process (it must not import Superstep) with the offline mock, and must
take the same path through the graph as the studio's mock run, with the same final state."""
import ast, json, os, re, subprocess, sys, uuid
from collections import Counter
import pytest
from fastapi.testclient import TestClient
from app.engine import agents, python_export as X, subgraphs, templating
from app.engine.compiler import pick_branch
from app.engine.decisions import mock as decision_mock
from app.engine.foreach import visible
from app.engine.llm import mock_agent, mock_llm
from app.engine.ports import Ports
from app.engine.runtime import run_stream
from app.engine.templates import BUILTINS
from app.api.deps import workflow_service
from app.main import app

KEYS = ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "TYPESAFE_API_KEY", "LLM_PROVIDER")
N = lambda i, t, **d: {"id": i, "type": t, "position": {"x": 0, "y": 0}, "data": {"label": i, **d}}  # noqa: E731
E = lambda s, t, label=None: {"id": f"{s}-{t}", "source": s, "target": t, **({"label": label} if label else {})}  # noqa: E731
L = lambda i, label, **d: {**N(i, "llm", **d), "data": {**d, "label": label}}  # noqa: E731
F = lambda name, t="string", r=None: {"name": name, "type": t, **({"reducer": r} if r else {})}  # noqa: E731

PARALLEL = {"name": "Parallel", "state": [F("message"), F("notes", "list", "append"), F("total", "number", "add"), F("summary")],
            "nodes": [N("start", "start"), N("a", "llm", prompt="Note A: {{state.message}}", output_field="notes",
                                                 retry={"max_attempts": 3, "initial_interval": 0.1}),
                      N("b", "llm", prompt="Note B: {{state.message | upper}}", output_field="notes", cache_ttl=60),
                      N("join", "join"), N("sum", "llm", prompt="Summarise {{state.notes | join(', ')}}", output_field="summary",
                                            input_fields=["notes"], timeout=30),
                      N("end", "end"), {"id": "n1", "type": "note", "position": {"x": 0, "y": 0}, "data": {"text": "Two notes\nin parallel"}}],
            "edges": [E("start", "a"), E("start", "b"), E("a", "join"), E("b", "join"), E("join", "sum"), E("sum", "end")]}

LOOP = {"name": "Loop", "state": [F("items", "list"), F("item"), F("i", "integer"), F("out", "list", "append"), F("kind")],
        "nodes": [N("start", "start"), N("each", "foreach", items_field="items", item_field="item", index_field="i", max_items=10),
                  N("work", "llm", prompt="Item {{state.i}}: {{state.item}}", output_field="out"),
                  N("classify", "llm", prompt="Classify this message: refund please", output_field="kind"),
                  N("route", "condition", field="kind"), N("r", "llm", prompt="Refund", output_field="out"),
                  N("g", "llm", prompt="Other", output_field="out"), N("end", "end")],
        "edges": [E("start", "each"), E("each", "work", "each"), E("work", "each"), E("each", "classify", "done"),
                  E("classify", "route"), E("route", "r", "refund"), E("route", "g", "default"), E("r", "end"), E("g", "end")]}

CHILD = {"name": "Review step", "state": [F("message"), F("verdict"), F("draft")],
         "nodes": [N("start", "start"), N("draft", "llm", prompt="Draft: {{state.message}}", output_field="draft"),
                   N("ask", "human", prompt="OK? {{state.draft}}", output_field="verdict"), N("end", "end")],
         "edges": [E("start", "draft"), E("draft", "ask"), E("ask", "end")]}
PARENT = {"name": "With a subgraph", "state": [F("message"), F("verdict"), F("answer")],
          "nodes": [N("start", "start"), N("review", "subgraph", workflow_id="child1"), N("check", "condition", field="verdict"),
                    N("yes", "llm", prompt="Send {{state.draft}}", output_field="answer"), N("end", "end")],
          "edges": [E("start", "review"), E("review", "check"), E("check", "yes", "approved"), E("check", "end", "rejected"),
                    E("yes", "end")]}

TOOLS = {"name": "Tools", "state": [F("message"), F("order"), F("size", "integer"), F("mcp", "object"), F("risk"), F("verdict", "object"), F("mail_to")],
         "nodes": [N("start", "start"), {**N("find", "tool", mode="function", function="lookup_order", output_field="order"),
                                              "data": {"label": "Lookup order", "mode": "function", "function": "lookup_order", "output_field": "order"}},
                   N("count", "tool", mode="code", output_field="size",
                     code='HELP = """two\nlines"""\n\ndef main(state):\n    return len(state["message"]) + len(HELP)\n'),
                   N("mcp", "mcp", tool="search", arguments={"q": "{{state.message}}", "n": 3}, output_field="mcp"),
                   N("decide", "decision", text="{{state.message}}", output_field="verdict",
                     questions=[{"id": "risk", "type": "choice", "instructions": "How risky?", "field": "risk",
                                 "options": [{"label": "low"}, {"label": "high"}]},
                                {"id": "s", "type": "score", "instructions": "Size", "levels": ["small", "big"]},
                                {"id": "y", "type": "noul", "instructions": "Urgent?"}]),
                   N("mail", "email", to="a@example.com; {{state.mail_to}}", subject="Hi", body="Order: {{state.order}}"),
                   N("end", "end")],
         "edges": [E("start", "find"), E("find", "count"), E("count", "mcp"), E("mcp", "decide"), E("decide", "mail"), E("mail", "end")]}

HTTP = {"name": "Http", "state": [F("message"), F("out", "object")],
        "nodes": [N("start", "start"), N("call", "tool", mode="http", method="POST", url="https://api.example.com/x",
                                         body='{"q": "{{state.message}}"}', output_field="out"), N("end", "end")],
        "edges": [E("start", "call"), E("call", "end")]}

ODD = {"name": "Đơn hàng: \"odd\" labels", "state": [F("message"), F("decision"), F("x")],
       "nodes": [N("start", "start"),
                 L("k", "class", prompt='Quote """ and \\ and {braces} {{state.message}}', output_field="x"),
                 L("d", "decision", prompt="x", output_field="decision"),
                 L("v", "Đơn hàng mới", prompt="Line one\nLine two", output_field="x"),
                 L("one", "1st step", prompt="1", output_field="x"),
                 L("p", "print", prompt="p", output_field="x"),
                 L("dup", "Đơn hàng mới", prompt="2", output_field="x"),
                 N("end", "end")],
       "edges": [E("start", "k"), E("k", "d"), E("d", "v"), E("v", "one"), E("one", "p"), E("p", "dup"), E("dup", "end")]}


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    for k in KEYS: monkeypatch.delenv(k, raising=False)


def picked(n):
    """A knowledge base and a server picked (their ports are stubs here), on the node or on an Agent node's tools."""
    if n["type"] in ("retriever", "mcp"): return {**n, "data": {**n["data"], "knowledge_base_id": "kb", "server_id": "srv"}}
    if n["type"] == "agent":
        return {**n, "data": {**n["data"], "tools": [{**t, "knowledge_base_id": "kb", "server_id": "srv"} if t.get("source") in ("knowledge", "mcp") else t
                                                     for t in n["data"].get("tools") or []]}}
    return n


def without_ms(state):
    """Tool call durations differ between two runs: the steps fields are compared without them."""
    return {k: [{a: b for a, b in x.items() if a != "ms"} if isinstance(x, dict) else x for x in v] if isinstance(v, list) else v
            for k, v in state.items()}


def studio(wf, inp, answers=None, children=None):
    """The studio's mock run: node ids in finish order and the final state. Human nodes get `answers` in order, and an
    Agent node's approvals the answers under the Agent node's id."""
    wf = subgraphs.expand(wf, (children or {}).get) if children else wf
    wf = {**wf, "nodes": [picked(n) for n in wf["nodes"]]}
    ports = Ports(retrieve=lambda *a: [], mcp_call=lambda *a: None, test=True, mock_models=True)
    left = {k: list(v) for k, v in (answers or {}).items()}
    path, resume = [], None
    while True:
        evs = list(run_stream(wf, inp, ports=ports, resume=resume))
        path += [e["node"] for e in evs if e["type"] == "node_finished"]
        last = evs[-1]
        if last["type"] != "run_waiting":
            assert last["type"] == "run_finished", last
            return path, visible(last["state"])
        resume = {**last["checkpoint"], "value": left[agents.agent_of_step(last["node"]) or last["node"]].pop(0)}


def exported(tmp_path, code):
    """Run an exported file in a fresh interpreter (-I: no PYTHONPATH, so no Superstep): node names and final state."""
    f = tmp_path / f"wf_{uuid.uuid4().hex[:6]}.py"; f.write_text(code)
    env = {k: v for k, v in os.environ.items() if k not in KEYS and k != "PYTHONPATH"}
    p = subprocess.run([sys.executable, "-I", str(f)], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL)
    assert p.returncode == 0, p.stderr[-3000:]
    names = [m.group(1) for m in re.finditer(r"^\[(\w+)\] ", p.stdout, re.M)]
    final = json.loads(p.stdout.split("Final state:", 1)[1])
    return names, final


def same_run(tmp_path, wf, inp, answers=None, children=None, ordered=True, ignore=()):
    out = X.to_python(wf, wf.get("name", "Workflow"), 1, children, {"input": inp, "answers": answers or {}})
    flat = agents.expand(subgraphs.expand(wf, (children or {}).get) if children else wf)
    kinds = {n["id"]: n["type"] for n in flat["nodes"]}
    path, state = studio(wf, inp, answers, children)
    want = [out.names[i] for i in path if kinds[i] not in ("start", "end", "subgraph", "subgraph_exit")]
    skip = {out.names[i] for i, t in kinds.items() if t == "subgraph"}
    got, final = exported(tmp_path, out.code)
    got = [n for n in got if n not in skip]
    assert (got if ordered else Counter(got)) == (want if ordered else Counter(want))
    final = {k: v for k, v in final.items() if not k.startswith(("loop_", "agent_")) and k not in ignore}
    assert without_ms(final) == without_ms({k: v for k, v in state.items() if k not in ignore})
    return out


def unused_imports(code):
    tree = ast.parse(code)
    imported = {(a.asname or a.name).split(".")[0] for n in ast.walk(tree) if isinstance(n, (ast.Import, ast.ImportFrom))
                for a in n.names if a.name != "annotations"}
    used = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    return imported - used


CASES = [(b["id"], i) for b in BUILTINS for i in range(len(b["tests"]))]


@pytest.mark.parametrize("tid,i", CASES)
def test_builtin_templates_take_the_studio_path(tmp_path, tid, i):
    b = next(x for x in BUILTINS if x["id"] == tid); case = b["tests"][i]
    out = same_run(tmp_path, b["workflow"], case["input"], case.get("answers"))
    assert unused_imports(out.code) == set() and out.filename.endswith(".py")


def test_parallel_join_reducers_and_policies(tmp_path):
    out = same_run(tmp_path, PARALLEL, {"message": "hi"}, ordered=False, ignore=("notes", "total"))  # parallel: either order
    code = out.code
    assert sorted(exported(tmp_path, code)[1]["notes"]) == sorted(studio(PARALLEL, {"message": "hi"})[1]["notes"])
    assert "retry_policy=RetryPolicy(max_attempts=3, initial_interval=0.1" in code and "cache_policy=CachePolicy(ttl=60)" in code
    assert "cache=InMemoryCache()" in code and 'builder.add_edge(["a", "b"], "join")' in code
    assert "notes: Annotated[list, append_items]" in code and "total: Annotated[float, add_numbers]" in code
    assert "input_schema=SumNodeInput" in code and "LangGraph has no timeout" in code
    assert "#   Two notes\n#   in parallel" in code and unused_imports(code) == set()


def test_for_each_condition_and_default(tmp_path):
    out = same_run(tmp_path, LOOP, {"items": ["x", "y", "z"]})
    assert 'builder.add_conditional_edges("each", route_each, {"each": "work", "done": "classify"})' in out.code
    assert 'return "default" if label is None else label' in out.code and '"recursion_limit": ' in out.code


def test_subgraph_is_its_own_graph(tmp_path):
    for answer in ("approved", "rejected"):
        out = same_run(tmp_path, PARENT, {"message": "hello"}, {"review/ask": [answer]}, {"child1": CHILD})
    code = out.code
    assert "class ReviewStepState(TypedDict, total=False):" in code and "def build_review_step():" in code
    assert 'builder.add_node("review", build_review_step())' in code and "interrupt(" in code
    assert out.names["review/ask"] == "ask" and "review" in out.names


def test_tools_decisions_mcp_and_email(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1"); monkeypatch.setenv("STUDIO_CODE_RUNTIME", "subprocess")
    out = same_run(tmp_path, TOOLS, {"message": "Order A100 is high priority", "mail_to": "b@example.com"}, ignore=("verdict",))
    code = out.code
    assert out.names["find"] == "lookup_order_node"  # the tool function keeps its own name
    assert 'ORDERS = {' in code and "def lookup_order(state" in code and "def lookup_order_node(state: State)" in code and "HELP = \"\"\"two\nlines\"\"\"" in code
    names, final = exported(tmp_path, code)
    assert final["size"] == len("Order A100 is high priority") + len("two\nlines") and final["risk"] == "high"
    assert final["verdict"]["s"] == {"type": "score", "score": 0.0} and final["sent"] if "sent" in final else True
    assert unused_imports(code) == set()


AGENT = {"name": "Agent sources", "state": [F("message"), F("answer"), F("steps", "list"), F("history", "list")],
         "nodes": [N("start", "start"), N("ag", "agent", label="Helper \"one\"", system_prompt="Be brief", prompt="{{state.message}}", output_field="answer",
                                          steps_field="steps", history_field="history", max_rounds=3, credential_id="cred-SECRET1",
                                          approval={"channel": "slack", "channel_id": "ch-SECRET2", "approvers": ["boss-SECRET3@x.io"]},
                                          tools=[{"name": "lookup_order", "description": "Find an order", "source": "builtin", "function": "lookup_order"},
                                                 {"name": "add", "description": "Add numbers", "source": "mcp", "server_id": "srv-SECRET4", "tool": "add",
                                                  "parameters": {"type": "object", "properties": {"a": {"type": "integer"}}, "required": ["a"]}, "approval": True},
                                                 {"name": "faq", "description": "Search the FAQ", "source": "knowledge", "knowledge_base_id": "kb-SECRET5", "top_k": 2},
                                                 {"name": "get_item", "description": "Get an item", "source": "http", "method": "GET", "url": "https://api.example.com/items"},
                                                 {"name": "post-it", "description": "Post a note", "source": "http", "method": "POST", "url": "https://api.example.com/{{state.args.id}}",
                                                  "body": '{"text": "{{state.args.text}}"}'}]),
                   N("end", "end")],
         "edges": [E("start", "ag"), E("ag", "end")]}


def test_agent_with_every_tool_source(tmp_path):
    out = same_run(tmp_path, AGENT, {"message": "find order B200", "history": [{"role": "user", "content": "hi"}]}, {"ag": ["approved"]})
    code = out.code
    assert "SECRET" not in code and unused_imports(code) == set() and "pip install langgraph httpx" in code
    assert [out.names[k] for k in ("ag", "ag/__model", "ag/__tool", "ag/__exit")] == ["helper_one", "helper_one_model", "helper_one_tool", "helper_one_end"]
    assert 'return call_mcp_tool("add", args)' in code and 'retrieve(str(args.get("query") or ""), top_k=2)' in code
    assert "params=query or None" in code and "body = json.dumps(args" not in code  # GET: query string; POST with a body template
    assert 'question = ("Helper \\"one\\" wants to call "' in code and "also go to a channel" in code
    assert 'builder.add_conditional_edges("helper_one_model", route_helper_one_model, {"tool": "helper_one_tool", "done": "helper_one_end"})' in code
    assert "agent_helper_one: Optional[dict]  # an Agent node's conversation" in code and '"recursion_limit": ' in code
    # the mock calls the MCP tool when the task names it, which needs approval: approve and reject both follow the studio
    for answer in ("approved", "No, use 2"):
        same_run(tmp_path, AGENT, {"message": "add numbers"}, {"ag": [answer]})


def test_http_tool_compiles_without_running():
    code = X.to_python(HTTP, "Http").code
    compile(code, "http.py", "exec")
    assert "import httpx" in code and 'httpx.request("POST"' in code and "pip install langgraph httpx" in code
    assert unused_imports(code) == set()


def test_odd_labels_give_valid_unique_names(tmp_path):
    out = same_run(tmp_path, ODD, {"message": "m"})
    names = [out.names[i] for i in ("k", "d", "v", "one", "p", "dup")]
    assert names == ["class_node", "decision_node", "don_hang_moi", "llm_1st_step", "print_node", "don_hang_moi_node"]
    assert all(n.isidentifier() for n in names) and len(set(names)) == len(names)
    assert out.filename == "don_hang_odd_labels.py" and '\'Quote """ and \\\\ and {braces}' not in out.code
    assert '"Quote \\"\\"\\" and \\\\ and {braces} {{state.message}}"' in out.code
    assert 'D_PROMPT' not in out.code and '"""Line one\nLine two"""' in out.code


def test_no_secret_reaches_the_file():
    wf = json.loads(json.dumps(TOOLS))
    secrets = {"credential_id": "cred-SECRET1", "api_key": "sk-SECRET2", "headers": {"Authorization": "Bearer SECRET3"},
               "server_id": "srv-SECRET4", "knowledge_base_id": "kb-SECRET5"}
    for n in wf["nodes"]: n["data"].update(secrets)
    wf["nodes"].append(N("ask", "human", prompt="?", output_field="risk",
                         approval={"channel": "slack", "channel_id": "ch-SECRET6", "target": "C-SECRET7", "approvers": ["boss-SECRET8@x.io"]},
                         deadline={"after": 3600, "then": "escalate", "escalate_to": ["esc-SECRET9@x.io"]}))
    code = X.to_python(wf, "Tools").code
    assert "SECRET" not in code and "also asks on Slack" in code


def test_same_graph_same_bytes_and_one_line_per_prompt_change():
    a = X.to_python(PARALLEL, "Parallel", 3).code
    moved = json.loads(json.dumps(PARALLEL)); moved["nodes"][1]["position"] = {"x": 500, "y": 9}
    assert X.to_python(moved, "Parallel", 3).code == a
    changed = json.loads(json.dumps(PARALLEL)); changed["nodes"][1]["data"]["prompt"] = "Note A again: {{state.message}}"
    diff = [x for x, y in zip(a.splitlines(), X.to_python(changed, "Parallel", 3).code.splitlines()) if x != y]
    assert len(diff) == 1 and len(a.splitlines()) == len(X.to_python(changed, "Parallel", 3).code.splitlines())


def test_spans_point_at_each_node():
    out = X.to_python(LOOP, "Loop")
    lines = out.code.splitlines()
    for nid, name in (("work", "work"), ("each", "each"), ("route", "route")):
        a, b = out.nodes[nid][0]
        assert lines[a - 1].startswith(("def ", f"{name.upper()}_")) and name in lines[a - 1].lower() and b >= a
    assert any("START" in lines[a - 1] for a, _ in out.nodes["start"]) and any("END" in lines[a - 1] for a, _ in out.nodes["end"])


SAMPLES = ["{{ state.a }}", "{{state.o.k}} {{state.l.1}} {{state.l.9}}", "{{state.a | upper | truncate(3)}}",
           "{{state.l | join(\"-\")}} {{state.n | default('none')}} {{state.o | json}} {{state.l | length}} {{state.l | first}}"]


def test_helpers_match_the_engine():
    ns: dict = {}
    head = "import json, os, re, string\nfrom typing import Any, Optional\n"
    exec(compile(head + X.TEMPLATES + X.MODEL + X.ROUTING + X.DECIDE, "helpers", "exec"), ns)
    state = {"a": "hello", "o": {"k": [1, 2]}, "l": ["x", "y"], "n": None}
    for t in SAMPLES:
        assert ns["render"](t, state) == templating.render(t, state)
    assert ns["render_args"]({"x": "{{state.o}}", "y": ["{{state.a}}!"]}, state) == templating.render_args({"x": "{{state.o}}", "y": ["{{state.a}}!"]}, state)
    for p in ("Classify this message: my order A100", "Classify: refund it", "Hello\nworld", ""):
        assert ns["mock_llm"](p, "m") == mock_llm(p, "m")
    for v, labels in (("Approved.", ["approved", "rejected"]), ("a b", ["a", "a b"]), ("x", ["y"]), ("yes", ["yes", "no"])):
        assert ns["pick_branch"](v, labels) == pick_branch(v, labels)
    exec(compile(head + X.MODEL + X.AGENT, "agent helpers", "exec"), ns)
    tools = [{"name": "add", "description": "Add numbers", "parameters": {"type": "object", "properties": {"a": {"type": "integer"}, "q": {"type": "string"}}, "required": ["a"]}},
             {"name": "find_order", "description": "Find an order", "parameters": {"type": "object", "properties": {"text": {"type": "string"}}}}]
    for msgs in ([{"role": "user", "content": "find order A100"}], [{"role": "system", "content": "s"}, {"role": "user", "content": "add 1"}],
                 [{"role": "user", "content": "x"}, {"role": "tool", "content": "done"}], []):
        for ts in (tools, None):
            assert ns["mock_agent"](msgs, ts, "m") == mock_agent(msgs, ts, "m")
    for schema, args in ((tools[0]["parameters"], {"a": 1}), (tools[0]["parameters"], {}), (tools[0]["parameters"], {"a": True}),
                         (tools[0]["parameters"], {"a": "1"}), (tools[0]["parameters"], [1]), ({"properties": {"x": {"type": ["string", "null"]}}}, {"x": 1})):
        assert ns["check_arguments"](schema, args) == agents.arg_error(schema, args)
    assert ns["shorten"]("x" * 10, 4) == agents.shorten("x" * 10, 4) and ns["tool_text"]({"a": 1}) == agents.text({"a": 1})
    body = {"state": "a HIGH risk", "questions": {"q": {"type": "choice", "instructions": "", "criteria": {"low": None, "high": None}}}}
    assert ns["decide"]("a HIGH risk", {"type": "choice", "instructions": "", "options": ["low", "high"]}) == decision_mock(body)["answers"]["q"]["choice"]


# ---- API ----


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client: yield client


H = lambda t: {"Authorization": f"Bearer {t}"}  # noqa: E731


def user(c):
    d = c.post("/api/auth/register", json={"email": f"t{uuid.uuid4().hex[:6]}@example.com", "password": "secret12"}).json()["data"]
    return {"token": d["token"], **d["user"]}


def save(c, u, wf):
    return c.post("/api/workflows", json={**wf, "name": f"{wf['name']} {uuid.uuid4().hex[:4]}"}, headers=H(u["token"])).json()["data"]["id"]


def test_api_serves_the_file_to_viewers(c):
    a, b, x = user(c), user(c), user(c)
    wid = save(c, a, CHILD)
    case = {"name": "ok", "input": {"message": "hi"}, "answers": {"ask": ["approved"]}, "checks": [{"kind": "status", "value": "ok"}]}
    assert c.post(f"/api/workflows/{wid}/tests", json=case, headers=H(a["token"])).status_code == 200
    r = c.get(f"/api/workflows/{wid}/python", headers=H(a["token"])).json()["data"]
    assert r["version"] == 1 and r["filename"].startswith("review_step_") and "EXAMPLE_ANSWERS = {\"ask\": [\"approved\"]}" in r["code"]
    assert r["nodes"]["ask"][0][0] > 1
    c.post("/api/workflows", json={**CHILD, "id": wid, "name": c.get(f"/api/workflows/{wid}", headers=H(a["token"])).json()["data"]["name"],
                                   "nodes": [n if n["id"] != "draft" else {**n, "data": {**n["data"], "prompt": "Version two"}} for n in CHILD["nodes"]]},
           headers=H(a["token"]))
    assert "Version two" in c.get(f"/api/workflows/{wid}/python", headers=H(a["token"])).json()["data"]["code"]
    assert "Version two" not in c.get(f"/api/workflows/{wid}/python?version=1", headers=H(a["token"])).json()["data"]["code"]
    assert c.get(f"/api/workflows/{wid}/python?version=9", headers=H(a["token"])).json()["error"]["code"] == "VERSION_NOT_FOUND"
    c.put(f"/api/workflows/{wid}/shares", json={"email": b["email"], "role": "viewer"}, headers=H(a["token"]))
    f = c.get(f"/api/workflows/{wid}/export/python", headers=H(b["token"]))
    assert f.status_code == 200 and f.headers["content-type"].startswith("text/x-python")
    assert re.match(r'attachment; filename="review_step_\w+\.py"', f.headers["content-disposition"]) and "StateGraph" in f.text
    assert c.get(f"/api/workflows/{wid}/python", headers=H(x["token"])).status_code == 404


def test_api_resolves_subgraphs_and_refuses_imports(c):
    u = user(c)
    child = save(c, u, CHILD)
    parent = json.loads(json.dumps(PARENT).replace('"child1"', json.dumps(child)))
    pid = save(c, u, parent)
    code = c.get(f"/api/workflows/{pid}/python", headers=H(u["token"])).json()["data"]["code"]
    assert "def build_review_step" in code and child not in code
    imp = save(c, u, CHILD)
    workflow_service().write_as(imp, "Imp", {**CHILD, "source": {"kind": "langgraph_import"}}, u["id"])  # only an import sets source
    r = c.get(f"/api/workflows/{imp}/python", headers=H(u["token"]))
    assert r.status_code == 400 and r.json()["error"]["code"] == "PYTHON_EXPORT_UNAVAILABLE"


def test_graph_values_never_become_code():
    """A shared graph can hold anything: numbers are checked, text is a literal or a comment, never code."""
    evil = "__import__('os').system('echo pwned')"
    wf = json.loads(json.dumps(PARALLEL))
    a, b = wf["nodes"][1]["data"], wf["nodes"][2]["data"]
    a.update(retry={"max_attempts": 2, "initial_interval": evil}, timeout=evil, label=f"x\r{evil}")
    b.update(cache_ttl=f"1){evil}", prompt=f"\r{evil}\n\"\"\"")
    wf["nodes"].append(N("r", "retriever", query="q", top_k=evil, output_field="summary"))
    wf["nodes"][6]["data"]["text"] = f"note\r{evil}\x0b{evil} {evil}"
    wf["edges"] += [E("sum", "r"), E("r", "end")]
    code = X.to_python(wf, f"Name\r{evil}", 1, example={"input": {"message": evil}}).code
    tree = ast.parse(code)
    assert not any(isinstance(n, ast.Name) and n.id == "__import__" for n in ast.walk(tree))
    assert "initial_interval=0.5" in code and "cache_policy" not in code and "top_k=4" in code
