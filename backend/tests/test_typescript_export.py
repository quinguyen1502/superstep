"""TASK-0082 (REQ-0047, DEC-0051): export a workflow as a runnable LangGraph.js TypeScript file; Agent nodes since TASK-0125.

Unit and snapshot tests always run. With Deno on the host (CI installs it for the Code-node tests), the exported files
are type-checked (`deno check`, npm: specifiers) and run, and must take the studio's mock path to the same final state.
The npm packages are fetched once into STUDIO_TS_EXPORT_DENO_DIR (default: a temp dir); offline, those tests skip."""
import json, os, re, shutil, subprocess, uuid
from collections import Counter
from pathlib import Path
import pytest
from app.engine import agents, exporters, subgraphs
from app.engine import typescript_export as T
from app.engine.templates import BUILTINS
from test_python_export import AGENT, CHILD, KEYS, LOOP, N, E, F, ODD, PARALLEL, PARENT, TOOLS, H, c, save, studio, user, without_ms  # noqa: F401

SNAPSHOT = Path(__file__).parent / "snapshots" / "typescript_export_demo.ts"
TS_CODE = ('import { z } from "npm:zod@^3"\n\nexport function main(state: State) {\n  console.log("got", state.message)\n'
           '  const msg = z.string().parse(state.message ?? "")\n  return { shout: msg.toUpperCase(), count: (state.count ?? 0) + 1 }\n}\n')
DEMO = {"name": "TypeScript demo", "state": [F("message"), F("count", "integer"), F("out", "object"), F("py"), F("tags", "list", "append")],
        "nodes": [N("start", "start"), N("c", "tool", mode="code", language="typescript", output_field="out", code=TS_CODE),
                  N("p", "tool", mode="code", language="python", code="def main(state):\n    return 1\n", output_field="py"),
                  N("end", "end")],
        "edges": [E("start", "c"), E("c", "end")]}


def demo():
    return T.to_typescript(DEMO, DEMO["name"], 3, {}, {"input": {"message": "xin chào", "count": 1}})


def test_snapshot():
    """The exact file for the demo graph (regenerate with UPDATE_SNAPSHOTS=1 after a deliberate change)."""
    code = demo().code
    if os.environ.get("UPDATE_SNAPSHOTS") == "1": SNAPSHOT.parent.mkdir(exist_ok=True); SNAPSHOT.write_text(code)
    assert code == SNAPSHOT.read_text()


def test_typescript_code_is_inlined_and_python_code_is_a_stub():
    out = demo(); code = out.code
    assert out.filename == "typescript_demo.ts" and code == demo().code  # deterministic
    assert code.count('import { z } from "npm:zod@^3"') == 1  # hoisted to the top, once
    assert "const CCode = (() => {\n  function main(state: State) {" in code and "export function main" not in code
    assert 'return asUpdate({ "out": await CCode(structuredClone(state)) });' in code
    assert "not implemented in TS export" in code and 'throw new Error("Tool node \\"p\\" (id: p) is python code' in code
    assert "p() is not connected to Start" in code and '.addNode("p"' not in code
    assert '"tags": Annotation<unknown[], unknown>({ reducer: appendItems, default: () => [] })' in code
    assert '"count": Annotation<number>()' in code and '"out": Annotation<Record<string, unknown>>()' in code
    assert out.nodes["c"][0][0] > 1 and out.names == {"c": "c", "p": "p"}


def test_policies_reducers_fan_in_and_inputs():
    code = T.to_typescript(PARALLEL, "Parallel").code
    assert "retryPolicy: { maxAttempts: 3, initialInterval: 100, backoffFactor: 1, jitter: false }" in code
    assert "cachePolicy: { ttl: 60 }" in code and "cache: new InMemoryCache()" in code and "timeout: 30000" in code
    assert '.addEdge(["a", "b"], "join")' in code and "input: SumInput" in code
    assert "reducer: addNumbers, default: () => 0" in code and "reducer: appendItems" in code


def test_every_node_type_maps_or_is_a_clear_stub():
    code = T.to_typescript(TOOLS, "Tools").code
    assert "TODO: search your own index" not in code  # no retriever in TOOLS
    assert "calls the Python function lookup_order: not implemented in TS export" in code
    assert "TODO: call the tool with an MCP client" in code and "await decide(text" in code and "(e-mail not sent)" in code
    loop = T.to_typescript(LOOP, "Loop").code
    assert '.addConditionalEdges("each", route_each, { "each": "work", "done": "classify" })' in loop and "recursionLimit:" in loop
    parent = T.to_typescript(PARENT, "P", None, {"child1": CHILD}).code
    assert "function build_review_step()" in parent and '.addNode("review", build_review_step())' in parent
    assert "interrupt({ node:" in parent and 'EXAMPLE_ANSWERS' in parent


def test_names_avoid_keywords_globals_and_helpers():
    wf = {"name": "x", "state": [F("x")], "nodes": [N("start", "start"), *[{**N(i, "llm", prompt="p", output_field="x"),
          "data": {"label": lab, "prompt": "p", "output_field": "x"}} for i, lab in (("a", "fetch"), ("b", "render"), ("c", "class"), ("d", "main"))],
          N("end", "end")], "edges": [E("start", "a"), E("a", "b"), E("b", "c"), E("c", "d"), E("d", "end")]}
    names = set(T.to_typescript(wf, "x").names.values())
    assert names.isdisjoint({"fetch", "render", "class", "main"}) and len(names) == 4


def test_credentials_and_values_never_become_code():
    evil = '"); Deno.exit(1); ("'
    wf = json.loads(json.dumps(PARALLEL))
    a = wf["nodes"][1]["data"]
    a.update(label=f"x*/\n{evil}\u2028{evil}", api_key="sk-secret-123", credential_id="cred1", retry={"max_attempts": evil})
    wf["nodes"].append({**N("h", "tool", mode="http", method="GET", url="https://x.example", headers={"Authorization": "Bearer sk-live-9"},
                           output_field="summary")})
    wf["edges"] += [E("sum", "h")]
    code = T.to_typescript(wf, f"Name */ {evil}", example={"input": {"message": evil}}).code
    assert "sk-secret-123" not in code and "sk-live-9" not in code and "cred1" not in code
    for ln in code.split("\n"):
        if "Deno.exit" in ln: assert ln.lstrip().startswith(("//", "*", "/**")) or '\\"' in ln, ln  # only in comments or literals
    assert "retryPolicy" not in code.split('.addNode("x')[1].split("\n")[0]


def test_registry_and_split_imports():
    assert set(exporters.EXPORTERS) == {"python", "typescript"} and exporters.EXPORTERS["typescript"].write is T.to_typescript
    imports, rest = T.split_imports('import {\n  a,\n} from "npm:x"\nimport "npm:y";\nexport default async function main() {}\nexport const k = 1\n')
    assert imports == ['import {\n  a,\n} from "npm:x"', 'import "npm:y";'] and rest == ["async function main() {}", "const k = 1"]


# ---- API ----


AGENT_PARENT = {"name": "Agent in a subgraph", "state": [F("message"), F("answer"), F("steps", "list")],
                "nodes": [N("start", "start"), N("sub", "subgraph", workflow_id="agent1"), N("end", "end")],
                "edges": [E("start", "sub"), E("sub", "end")]}


def test_agent_nodes_are_exported(c):
    """TASK-0125: the Agent node's steps, as in the Python file, with no credential or id of the studio's."""
    out = T.to_typescript(AGENT, "Agent")
    code = out.code
    assert "SECRET" not in code and "--allow-net" in code and "callAgent" in code
    assert [out.names[k] for k in ("ag", "ag/__model", "ag/__tool", "ag/__exit")] == ["helper_one", "helper_one_model", "helper_one_tool", "helper_one_end"]
    assert '"agent_helper_one": Annotation<AgentChat | null>(),  // an Agent node\'s conversation' in code
    assert 'return await callMcpTool("add", args);' in code and 'return await retrieve(String(args.query || ""), 2);' in code
    assert "they go in the query string" in code and 'method: "POST", body: body || undefined' in code  # GET: query string; POST: its body template
    assert 'throw new Error("lookup_order is a Python function' in code and "here they throw" in code
    assert 'const question = "Helper \\"one\\" wants to call " + call.name' in code and "also go to a channel" in code
    assert '.addConditionalEdges("helper_one_model", route_helper_one_model, { tool: "helper_one_tool", done: "helper_one_end" })' in code
    assert '.addEdge("helper_one_end", END)' in code and "recursionLimit: " in code
    assert "def helper_one" not in code and "helper_one_end" in T.to_typescript(AGENT_PARENT, "P", None, {"agent1": AGENT}).code
    u = user(c); wid = save(c, u, AGENT)
    r = c.get(f"/api/workflows/{wid}/code?language=typescript", headers=H(u["token"])).json()["data"]
    assert r["language"] == "typescript" and "async function helper_one_tool(" in r["code"]


def test_api_language_parameter(c):
    u = user(c)
    wid = save(c, u, PARALLEL)  # saving Code nodes needs code.write; the exporter is the same
    r = c.get(f"/api/workflows/{wid}/code?language=typescript", headers=H(u["token"])).json()["data"]
    assert r["language"] == "typescript" and r["filename"].endswith(".ts") and "Annotation.Root" in r["code"]
    assert c.get(f"/api/workflows/{wid}/python", headers=H(u["token"])).json()["data"]["language"] == "python"
    f = c.get(f"/api/workflows/{wid}/export/typescript", headers=H(u["token"]))
    assert f.status_code == 200 and f.headers["content-type"].startswith("text/typescript")
    assert re.match(r'attachment; filename="parallel_\w+\.ts"', f.headers["content-disposition"])
    bad = c.get(f"/api/workflows/{wid}/code?language=rust", headers=H(u["token"])).json()
    assert bad["error"]["code"] == "EXPORT_LANGUAGE_UNSUPPORTED" and bad["error"]["details"]["supported"] == "python, typescript"
    from app.api.deps import workflow_service
    workflow_service().write_as(wid, "Imp", {**PARALLEL, "source": {"kind": "langgraph_import"}}, u["id"])
    assert c.get(f"/api/workflows/{wid}/code?language=typescript", headers=H(u["token"])).json()["error"]["code"] == "TYPESCRIPT_EXPORT_UNAVAILABLE"


# ---- Deno: type-check and run ----

DENO = shutil.which("deno")


@pytest.fixture(scope="module")
def deno_env(tmp_path_factory):
    if not DENO: pytest.skip("deno is not installed")
    cache = os.environ.get("STUDIO_TS_EXPORT_DENO_DIR") or str(tmp_path_factory.mktemp("deno"))
    env = {k: v for k, v in os.environ.items() if k not in KEYS}
    env.update(DENO_DIR=cache, NO_COLOR="1")
    probe = tmp_path_factory.mktemp("probe") / "p.ts"
    probe.write_text(demo().code)
    p = subprocess.run([DENO, "check", "-q", str(probe)], env=env, capture_output=True, text=True, timeout=600)
    if p.returncode and re.search(r"error sending request|dns error|Connection refused|failed to fetch|Could not find npm package", p.stderr, re.I):
        pytest.skip(f"npm registry unreachable: {p.stderr[-300:]}")
    assert p.returncode == 0, p.stderr[-3000:]
    return env


def ts_run(tmp_path, env, code, check=True):
    f = tmp_path / f"wf_{uuid.uuid4().hex[:6]}.ts"; f.write_text(code)
    if check:
        p = subprocess.run([DENO, "check", "-q", str(f)], env=env, capture_output=True, text=True, timeout=300)
        assert p.returncode == 0, p.stderr[-3000:]
    p = subprocess.run([DENO, "run", "-q", "--allow-env", "--allow-read", str(f)], cwd=tmp_path, env=env, capture_output=True,
                       text=True, timeout=120, stdin=subprocess.DEVNULL)
    assert p.returncode == 0, p.stderr[-3000:]
    names = [m.group(1) for m in re.finditer(r"^\[(\w+)\] ", p.stdout, re.M)]
    return names, json.loads(p.stdout.split("Final state:", 1)[1]), p.stdout


def same_run(tmp_path, env, wf, inp, answers=None, children=None, ordered=True, ignore=()):
    out = T.to_typescript(wf, wf.get("name", "Workflow"), 1, children, {"input": inp, "answers": answers or {}})
    flat = agents.expand(subgraphs.expand(wf, (children or {}).get) if children else wf)
    kinds = {n["id"]: n["type"] for n in flat["nodes"]}
    path, state = studio(wf, inp, answers, children)
    want = [out.names[i] for i in path if kinds[i] not in ("start", "end", "subgraph", "subgraph_exit")]
    skip = {out.names[i] for i, t in kinds.items() if t == "subgraph"}
    got, final, _ = ts_run(tmp_path, env, out.code)
    got = [n for n in got if n not in skip]
    assert (got if ordered else Counter(got)) == (want if ordered else Counter(want))
    final = {k: v for k, v in final.items() if not k.startswith(("loop_", "agent_")) and k not in ignore}
    assert without_ms(final) == without_ms({k: v for k, v in state.items() if k not in ignore})
    return out


def test_demo_type_checks_and_runs_the_typescript_code_node(tmp_path, deno_env):
    _, final, stdout = ts_run(tmp_path, deno_env, demo().code)
    assert "got xin chào" in stdout and final["out"] == {"shout": "XIN CHÀO", "count": 2} and final["tags"] == []


def test_parallel_loop_and_subgraph_take_the_studio_path(tmp_path, deno_env):
    same_run(tmp_path, deno_env, PARALLEL, {"message": "hi"}, ordered=False, ignore=("notes", "total"))
    same_run(tmp_path, deno_env, LOOP, {"items": ["a", "b"]})
    same_run(tmp_path, deno_env, PARENT, {"message": "hi"}, {"review/ask": ["approved"]}, {"child1": CHILD})
    same_run(tmp_path, deno_env, ODD, {"message": "x"})


def test_agent_takes_the_studio_path(tmp_path, deno_env):
    """The mock calls the tool the task names: an MCP tool that needs approval (approved, rejected with a reason), a
    knowledge base, and the same inside a subgraph."""
    history = [{"role": "user", "content": "hi"}, {"role": "assistant", "content": "hello"}]
    for answer in ("approved", "No, use 2"):
        same_run(tmp_path, deno_env, AGENT, {"message": "add numbers", "history": history}, {"ag": [answer]})
    same_run(tmp_path, deno_env, AGENT, {"message": "search the faq"})
    same_run(tmp_path, deno_env, AGENT_PARENT, {"message": "add numbers"}, {"sub/ag": ["rejected"]}, {"agent1": AGENT})


def test_agent_builtin_tools_are_stubs_the_model_hears_about(tmp_path, deno_env):
    out = T.to_typescript(AGENT, "Agent", 1, None, {"input": {"message": "find order B200"}})
    _, final, _ = ts_run(tmp_path, deno_env, out.code)
    assert [s["status"] for s in final["steps"]] == ["error"] and final["steps"][0]["tool"] == "lookup_order"
    assert final["answer"] == "[mock:gpt-4o-mini] Answer: The tool failed: lookup_order is a Python function of the Superstep server: not implemented in TS export"


def test_all_node_types_type_check(tmp_path, deno_env):
    support = next(b["workflow"] for b in BUILTINS if any(n["type"] == "agent" for n in b["workflow"]["nodes"]))
    for wf in (TOOLS, AGENT, support):
        ts_run_check = tmp_path / "t.ts"; ts_run_check.write_text(T.to_typescript(wf, wf.get("name", "Workflow")).code)
        p = subprocess.run([DENO, "check", "-q", str(ts_run_check)], env=deno_env, capture_output=True, text=True, timeout=300)
        assert p.returncode == 0, p.stderr[-3000:]


def python_functions(n: dict) -> bool:
    d = n.get("data") or {}
    if n["type"] == "agent": return any(isinstance(t, dict) and t.get("source") == "builtin" for t in d.get("tools") or [])
    return n["type"] == "tool" and d.get("mode", "function") == "function"


RUNNABLE = [(b["id"], i) for b in BUILTINS for i in range(len(b["tests"]))
            if not any(python_functions(n) for n in b["workflow"]["nodes"])]  # TypeScript cannot run the server's Python functions


@pytest.mark.parametrize("tid,i", RUNNABLE)
def test_builtin_templates_take_the_studio_path(tmp_path, deno_env, tid, i):
    b = next(x for x in BUILTINS if x["id"] == tid); case = b["tests"][i]
    same_run(tmp_path, deno_env, b["workflow"], case["input"], case.get("answers"))
