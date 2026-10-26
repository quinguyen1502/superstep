"""Agent nodes (TASK-0116, REQ-0072, DEC-0063): the model picks and calls the tools the node allows, round after round,
until it answers.

An Agent node `A` is expanded before compilation, as subgraph nodes are, into ordinary LangGraph steps:
    A (entry: builds the conversation) → A/__model (one model call) ⇄ A/__tool (one tool call) → A/__exit (the answer)
so every model call and every tool call checkpoints, recovers and uses the side-effect ledger on its own: a pause, a
crash or a restart repeats at most the step that had not finished. The conversation lives in the hidden state field
`agent:A` (plain JSON): {messages, pending, rounds, limit_hit, steps, answer, last}.

Node data: credential_id, model, system_prompt, prompt, output_field, steps_field?, history_field?, max_rounds and
`tools`, each {name, description, source: mcp | http | builtin | knowledge | workflow, approval?} plus its source's settings:
  mcp: server_id, tool, parameters (the server's input schema)    builtin: function (engine/tools.py)
  knowledge: knowledge_base_id, top_k                               http: method, url, body, parameters
  workflow: workflow_id, inputs (the state fields the model fills), outputs (the final state fields it gets back)
A workflow tool (REQ-0073, DEC-0066) gets `snapshot` and `version` when a run is planned (`snapshot()`): the child's latest
saved workflow, so a paused or recovered run calls the same version.
HTTP templates read the model's arguments as `{{state.args.<name>}}`; without a body, POST/PUT/PATCH send the
arguments as JSON, and a GET whose URL does not use them gets them as query parameters.

Approval (TASK-0117, DEC-0063 decision 7): before a call to a tool with `approval: true`, `A/__tool` pauses the run like a
Human node (`Interrupt`), with the Agent node's `approval` and `deadline` settings (copied onto the step by `expand`), so
the Approvals inbox, the channels and the deadlines work unchanged. The answer `approved` runs the call; `rejected` or
any other text rejects it, and the model gets "Rejected by a reviewer" plus that text as the tool result.
"""
from __future__ import annotations
import copy, json, re, time
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode
from ..core import config
from ..core.errors import AppError
from .effects import Effects, call_tool
from .errors import AwaitChild, Interrupt, ValidationError
from .issues import Issue
from .limits import safe_error
from .llm import call_agent
from .ports import Ports
from .state_schema import state_schema
from . import subgraphs
from .templating import refs, render
from .tools import PARAMETERS, TOOLS

PREFIX, SEP = "agent:", "/"
MODEL, TOOL, EXIT = "__model", "__tool", "__exit"
TYPES = ("agent", "agent_model", "agent_tool", "agent_exit")
ROUTERS = ("agent_model", "agent_tool")  # steps that pick the next step (they may loop)
SOURCES = ("mcp", "http", "builtin", "knowledge", "workflow")
DEFAULT_ROUNDS, MAX_ROUNDS, MAX_CALLS_PER_ROUND = 5, 25, 8
RESULT_CHARS = 8000  # a tool result goes back to the model shortened to this
STEP_CHARS = 2000    # ... and into the steps field / trace shortened to this
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
QUERY = {"type": "object", "properties": {"query": {"type": "string", "description": "What to search for"}}, "required": ["query"]}
APPROVED, REJECTED = "approved", "rejected"
FAILED = "The tool failed"  # the result of a call that ran and raised (checks.py tells it from calls that never ran)
ASK = {"en": "{agent} wants to call {tool} with these arguments:\n{args}\nApprove to run it, or reject it. A text reply rejects it and tells the model why.",
       "vi": "{agent} muốn gọi công cụ {tool} với các tham số:\n{args}\nDuyệt để chạy, hoặc từ chối. Trả lời bằng chữ là từ chối và cho model biết lý do."}
JSON_TYPES = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list, "object": dict}


def private(nid: str) -> str: return PREFIX + nid


def visible(state: Dict[str, Any]) -> Dict[str, Any]:
    """State without the agents' conversations (the run's output, the trace)."""
    return {k: v for k, v in state.items() if not k.startswith(PREFIX)}


def owner(node: Dict[str, Any]) -> str:
    """The Agent node an expanded step belongs to."""
    return (node.get("data") or {}).get("agent_of") or node["id"]


def agent_of_step(nid: str) -> Optional[str]:
    """`A` for the tool step `A/__tool`, whose approvals test cases answer under the Agent node's id (TASK-0117)."""
    tail = SEP + TOOL
    return nid[:-len(tail)] if nid.endswith(tail) else None


def step_of(delta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """What an agent step did, for its `node_finished` event (the delta itself leaves the conversation out)."""
    return next((v["last"] for k, v in delta.items() if k.startswith(PREFIX) and isinstance(v, dict) and v.get("last") is not None), None)


# ---- tools ------------------------------------------------------------------------------------

def parameters(t: Dict[str, Any]) -> Dict[str, Any]:
    src = t.get("source")
    if src == "knowledge": return QUERY
    if src == "builtin": return PARAMETERS.get(t.get("function") or "") or {"type": "object", "properties": {}}
    if src == "workflow":  # the child's state fields the model fills, typed from the snapshot once a run is planned
        props, want = state_schema(t.get("snapshot") or {})["properties"], field_list(t.get("inputs"))
        return {"type": "object", "properties": {f: props.get(f) or {"type": "string"} for f in want}, "required": want}
    p = t.get("parameters")
    return p if isinstance(p, dict) and p else {"type": "object", "properties": {}}


def specs(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The tools as the model sees them."""
    return [{"name": t.get("name") or "", "description": t.get("description") or "", "parameters": parameters(t)}
            for t in d.get("tools") or [] if isinstance(t, dict)]


def arg_error(schema: Dict[str, Any], args: Any) -> Optional[str]:
    """Required properties and JSON types of the top-level arguments (no full JSON Schema)."""
    if not isinstance(args, dict): return "arguments must be a JSON object"
    props = schema.get("properties") or {}
    missing = [k for k in schema.get("required") or [] if k not in args]
    if missing: return f"missing argument(s): {', '.join(missing)}"
    for k, v in args.items():
        want = (props.get(k) or {}).get("type") if isinstance(props.get(k), dict) else None
        if not isinstance(want, str) or want not in JSON_TYPES or v is None: continue  # type lists (["string", "null"]) pass
        ok = isinstance(v, JSON_TYPES[want]) and not (want in ("number", "integer") and isinstance(v, bool))
        if not ok: return f"argument {k} must be of type {want}"
    return None


def field_list(v: Any) -> List[str]:
    return [f for f in v if isinstance(f, str)] if isinstance(v, list) else []


def text(v: Any) -> str:
    return v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, default=str)


def shorten(s: str, n: int) -> str:
    return s if len(s) <= n else s[:n] + f"… (shortened from {len(s)} characters)"


def http_request(nid: str, t: Dict[str, Any], args: Dict[str, Any], state: Dict[str, Any], headers: Dict[str, str]) -> Any:
    """The builder's templates are rendered once; the model's arguments are inserted as values and never rendered, so an
    argument that looks like `{{state.x}}` cannot read other state fields."""
    from .nodes import http_send  # nodes dispatches to this module
    method, tpl_url, tpl_body = (t.get("method") or "GET").upper(), t.get("url") or "", t.get("body") or ""
    ctx = {**state, "args": args}
    url, body = render(tpl_url, ctx), render(tpl_body, ctx)
    uses_args = any(r.field == "args" for r in refs(tpl_url) + refs(tpl_body))
    if not tpl_body and method in ("POST", "PUT", "PATCH"): body = json.dumps(args, ensure_ascii=False)
    elif method == "GET" and args and not uses_args: url += ("&" if "?" in url else "?") + urlencode({k: text(v) for k, v in args.items()})
    return http_send(nid, method, url, body, headers)


def run_tool(nid: str, t: Dict[str, Any], args: Dict[str, Any], state: Dict[str, Any], ports: Ports, effects: Optional[Effects]) -> Any:
    src = t.get("source")
    if src == "mcp":
        if ports.mcp_call is None: raise RuntimeError("Agent MCP tools need the MCP service")
        return ports.mcp_call(t.get("server_id") or "", t.get("tool") or "", args)
    if src == "knowledge":
        if ports.retrieve is None: raise RuntimeError("Agent knowledge base tools need a knowledge base service")
        return ports.retrieve(t.get("knowledge_base_id") or "", str(args.get("query") or ""), int(t.get("top_k") or 4))
    if src == "builtin":
        return call_tool(TOOLS[t["function"]], {**state, **args}, effects.key(nid) if effects else None, ports.locale)
    if src == "http":
        if config.demo_mode(): raise AppError("DEMO_NODE_DISABLED", node="HTTP Tool")
        return http_request(nid, t, args, state, effects.headers(nid) if effects else {})
    raise RuntimeError(f"unknown tool source {src!r}")


# ---- validation -------------------------------------------------------------------------------

def errors(nid: str, d: Dict[str, Any], schema: List[Dict[str, Any]]) -> List[str]:
    """Settings errors of one Agent node (the validator adds output_field and template checks)."""
    errs, types = [], {f["name"]: f.get("type", "string") for f in schema}
    if not str(d.get("prompt") or "").strip(): errs.append(Issue("AGENT_PROMPT_MISSING", node=nid))
    r = d.get("max_rounds", DEFAULT_ROUNDS)
    if not isinstance(r, int) or isinstance(r, bool) or not 1 <= r <= MAX_ROUNDS: errs.append(Issue("AGENT_ROUNDS", node=nid, max=MAX_ROUNDS))
    for key, want in (("steps_field", "list"), ("history_field", "list")):
        f = d.get(key)
        if f and types and f not in types: errs.append(Issue("AGENT_FIELD_UNKNOWN", node=nid, key=key, field=f))
        elif f and types and types[f] != want: errs.append(Issue("AGENT_FIELD_NOT_LIST", node=nid, key=key, field=f))
    tools = d.get("tools")
    if not isinstance(tools, list) or not tools: return errs + [Issue("AGENT_TOOLS_MISSING", node=nid)]
    seen = set()
    for i, t in enumerate(tools, 1):
        if not isinstance(t, dict): errs.append(Issue("AGENT_TOOL_NOT_OBJECT", node=nid, index=i)); continue
        name, src = t.get("name") or "", t.get("source")
        who = {"node": nid, "tool": name or i}
        if not NAME_RE.match(name): errs.append(Issue("AGENT_TOOL_NAME", **who))
        elif name in seen: errs.append(Issue("AGENT_TOOL_DUPLICATE", node=nid, tool=name))
        seen.add(name)
        if src not in SOURCES: errs.append(Issue("AGENT_TOOL_SOURCE", **who, source=src)); continue
        if src == "mcp" and not (t.get("server_id") and t.get("tool")): errs.append(Issue("AGENT_TOOL_MCP", **who))
        if src == "builtin" and t.get("function") not in TOOLS: errs.append(Issue("AGENT_TOOL_FUNCTION", **who, function=t.get("function")))
        if src == "knowledge":
            if not t.get("knowledge_base_id"): errs.append(Issue("AGENT_TOOL_KB", **who))
            k = t.get("top_k", 4)
            if not isinstance(k, int) or isinstance(k, bool) or not 1 <= k <= 20: errs.append(Issue("AGENT_TOOL_TOP_K", **who))
        if src == "workflow":
            if not t.get("workflow_id"): errs.append(Issue("AGENT_TOOL_WORKFLOW", **who))
            for key, code in (("inputs", "AGENT_TOOL_INPUTS"), ("outputs", "AGENT_TOOL_OUTPUTS")):
                v, names = t.get(key), field_list(t.get(key))
                bad = v is not None and (not isinstance(v, list) or len(names) != len(v) or len(set(names)) != len(names) or not all(names))
                if bad or (key == "outputs" and not names): errs.append(Issue(code, **who))
        if src == "http":
            if not t.get("url"): errs.append(Issue("AGENT_TOOL_URL", **who))
            if (t.get("method") or "GET").upper() not in METHODS: errs.append(Issue("AGENT_TOOL_METHOD", **who, methods=", ".join(METHODS)))
        p = t.get("parameters")
        if p is not None and (not isinstance(p, dict) or not isinstance(p.get("properties", {}), dict) or p.get("type", "object") != "object"):
            errs.append(Issue("AGENT_TOOL_PARAMETERS", **who))
    return errs


def needs_approval(d: Dict[str, Any]) -> bool:
    return any(isinstance(t, dict) and t.get("approval") for t in d.get("tools") or [])


def templates(d: Dict[str, Any]) -> List[str]:
    """Templates rendered with the run state (HTTP tool templates are checked without `state.args`)."""
    out = [d.get("system_prompt") or "", d.get("prompt") or ""]
    for t in d.get("tools") or []:
        if isinstance(t, dict) and t.get("source") == "http": out += [t.get("url") or "", t.get("body") or ""]
    return out


def fields(d: Dict[str, Any]) -> List[str]:
    return [f for f in (d.get("output_field"), d.get("steps_field")) if f]


# ---- expansion --------------------------------------------------------------------------------

def has_agents(wf: Dict[str, Any]) -> bool:
    return any(isinstance(n, dict) and n.get("type") == "agent" and not (n.get("data") or {}).get("agent_expanded") for n in wf.get("nodes", []))


def expand(wf: Dict[str, Any]) -> Dict[str, Any]:
    """The workflow with each Agent node followed by its model, tool and exit steps (idempotent; the input is not changed)."""
    if not has_agents(wf): return wf
    out = copy.deepcopy(wf); nodes, edges = out["nodes"], out.get("edges") or []
    for n in [n for n in nodes if isinstance(n, dict) and n.get("type") == "agent" and not (n.get("data") or {}).get("agent_expanded")]:
        a, d = n["id"], n.get("data") or {}
        label = d.get("label") or a
        n["data"] = {**d, "agent_expanded": True}
        # a cached step would skip its model or tool call (and its approval) on a run with the same state: only the
        # entry step keeps the node's cache and input fields; retry and timeout apply to each step
        inner = {k: v for k, v in d.items() if k not in ("label", "cache_ttl", "input_fields")}
        # a workflow tool's child snapshot is run by the tool step only: the other steps keep its state fields (the
        # parameter types), which keeps the checkpoint small
        lean = {**inner, "tools": [{**t, "snapshot": {"state": t["snapshot"].get("state") or []}}
                                   if isinstance(t, dict) and isinstance(t.get("snapshot"), dict) else t for t in d.get("tools") or []]}
        step = lambda suffix, typ, name, data: {"id": f"{a}{SEP}{suffix}", "type": typ, "position": n.get("position"),
                                                "data": {**data, "label": f"{label} › {name}", "agent_of": a, "agent_label": label}}
        n["data"] = {**n["data"], "tools": lean["tools"]} if "tools" in d else n["data"]
        nodes += [step(MODEL, "agent_model", "model", lean), step(TOOL, "agent_tool", "tool", inner), step(EXIT, "agent_exit", "end", lean)]
        m, t, x = f"{a}{SEP}{MODEL}", f"{a}{SEP}{TOOL}", f"{a}{SEP}{EXIT}"
        edges[:] = [{**e, "source": x} if e.get("source") == a else e for e in edges]  # the agent's way out
        edges += [{"id": f"{a}{SEP}e-model", "source": a, "target": m},
                  {"id": f"{a}{SEP}e-call", "source": m, "target": t, "label": "tool"},
                  {"id": f"{a}{SEP}e-done", "source": m, "target": x, "label": "done"},
                  {"id": f"{a}{SEP}e-next", "source": t, "target": t, "label": "tool"},
                  {"id": f"{a}{SEP}e-back", "source": t, "target": m, "label": "model"}]
    out["edges"] = edges
    return out


def snapshot(wf: Dict[str, Any], load: subgraphs.Loader, self_id: Optional[str] = None,
             version: Optional[Callable[[str, Dict[str, Any]], Optional[int]]] = None) -> Dict[str, Any]:
    """The workflow with each workflow tool's child copied in as `snapshot` (DEC-0066 decision 2): the child's latest saved
    workflow with its subgraphs expanded and its own workflow tools snapshotted, and `version(id, child)` as `version`.
    Run after `subgraphs.expand`, so Agent nodes inside subgraphs are covered. Raises ValidationError (references).
    Snapshots that came with the workflow are dropped first: only the ones made here are run."""
    sent = [t for n in wf.get("nodes", []) if isinstance(n, dict) for t in (n.get("data") or {}).get("tools") or []
            if isinstance(t, dict) and ("snapshot" in t or "version" in t)]
    if sent:
        wf = copy.deepcopy(wf)
        for n in wf["nodes"]:
            for t in (n.get("data") or {}).get("tools") or [] if isinstance(n, dict) else []:
                if isinstance(t, dict): t.pop("snapshot", None); t.pop("version", None)
    if not subgraphs.tool_refs(wf): return wf
    errs = subgraphs.check(wf, load, self_id)
    if errs: raise ValidationError(errs)
    def snap(w: Dict[str, Any]) -> Dict[str, Any]:  # check() ruled out cycles and bounded the depth
        out = copy.deepcopy(w)
        for _, t in subgraphs.tool_refs(out):
            raw = load(t["workflow_id"]) or {}
            t["snapshot"] = snap(subgraphs.expand(raw, load, t["workflow_id"]))
            t["version"] = version(t["workflow_id"], raw) if version else None
        return out
    return snap(wf)


def step_budget(wf: Dict[str, Any]) -> int:
    """Extra LangGraph steps the Agent nodes may need: each round is a model call plus up to MAX_CALLS_PER_ROUND tool calls,
    and the last call without tools, the entry and the exit come on top."""
    total = 0
    for n in wf.get("nodes", []):
        if isinstance(n, dict) and n.get("type") == "agent":
            r = (n.get("data") or {}).get("max_rounds", DEFAULT_ROUNDS)
            r = r if isinstance(r, int) and not isinstance(r, bool) and 1 <= r <= MAX_ROUNDS else DEFAULT_ROUNDS
            total += r * (1 + MAX_CALLS_PER_ROUND) + 3
    return total


def router(node: Dict[str, Any]) -> Callable[[dict], str]:
    """After a model step: `tool` while calls are pending, else `done`. After a tool step: `tool` or back to `model`."""
    key, back = private(owner(node)), "done" if node["type"] == "agent_model" else "model"
    return lambda state: "tool" if ((state.get(key) or {}).get("pending")) else back


# ---- steps ------------------------------------------------------------------------------------

def answer(resume: Optional[Dict[str, Any]], nid: str) -> Optional[str]:
    """The approver's answer for this step, consumed once (as for a Human node) so a later call to the tool asks again."""
    if resume is not None and resume.get("node") == nid and "value" in resume: return str(resume.pop("value"))
    return None


def child_result(resume: Optional[Dict[str, Any]], nid: str) -> Optional[Dict[str, Any]]:
    """The finished child run of a workflow tool call, consumed once: {child_run_id, status, output, error, usage}. The
    run service sends it as a dict; a person's answer is always text, so it can never pass for one (TASK-0134)."""
    v = resume.get("value") if resume is not None and resume.get("node") == nid else None
    if isinstance(v, dict) and "child_run_id" in v: return resume.pop("value")
    return None


def child_outcome(t: Dict[str, Any], got: Dict[str, Any]) -> tuple:
    """(status, result text) of a workflow tool call from its finished child run."""
    if got.get("status") == "ok":
        final = got.get("output") or {}
        return "ok", text({f: final.get(f) for f in field_list(t.get("outputs"))})
    why = got.get("error") or got.get("status") or "unknown"
    return "error", f"{FAILED}: the workflow ended with {got.get('status')}: {why}"


def rejection(response: str) -> str:
    comment = "" if response.strip().lower() == REJECTED else response.strip()
    return "Rejected by a reviewer" + (f": {comment}" if comment else "")


def node_fn(node: Dict[str, Any], resolve=None, usage=None, effects: Optional[Effects] = None, ports: Optional[Ports] = None,
            offline: bool = False, tokens: Optional[Callable[[str], Any]] = None, resume: Optional[Dict[str, Any]] = None) -> Callable[[dict], dict]:
    """tokens(nid) -> a TokenBuffer for the run stream, or None (engine/nodes.token_stream).
    resume: {"node", "value"} when the run continues after an approval (engine/runtime)."""
    ports = ports or Ports()
    t, d, nid = node["type"], node.get("data") or {}, node["id"]
    key = private(owner(node))

    if t == "agent":
        def fn(state):
            msgs = [{"role": "system", "content": render(d["system_prompt"], state)}] if d.get("system_prompt") else []
            for m in (state.get(d["history_field"]) or []) if d.get("history_field") else []:
                if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str):
                    msgs.append({"role": m["role"], "content": m["content"]})
            msgs.append({"role": "user", "content": render(d.get("prompt") or "", state)})
            return {key: {"messages": msgs, "pending": [], "rounds": 0, "limit_hit": False, "steps": [], "answer": None, "last": None}}
        return fn

    if t == "agent_model":
        limit = d.get("max_rounds", DEFAULT_ROUNDS)
        def fn(state):
            p = copy.deepcopy(state.get(key) or {})
            hit = p.get("rounds", 0) >= limit  # the round limit: one more call without tools for the answer
            cred = None
            if d.get("credential_id") and not offline:
                if resolve is None: raise RuntimeError("Node uses a credential but no resolver is available")
                cred = resolve(d["credential_id"])
            buf = tokens(nid) if tokens else None
            try:
                out, calls = call_agent(p.get("messages") or [], None if hit else specs(d), d.get("model") or "gpt-4o-mini", cred,
                                        (lambda u: usage(nid, u)) if usage else None, buf, mock=offline, locale=ports.locale)
            finally:
                if buf: buf.flush()
            calls = [] if hit else [{"id": str(c.get("id") or f"call_{i}"), "name": str(c.get("name") or ""), "args": c.get("args")}
                                    for i, c in enumerate(calls)]
            if not hit: p["rounds"] = p.get("rounds", 0) + 1
            p["limit_hit"] = hit
            p.setdefault("messages", []).append({"role": "assistant", "content": out, **({"tool_calls": calls} if calls else {})})
            p["pending"] = calls[:MAX_CALLS_PER_ROUND]
            for c in calls[MAX_CALLS_PER_ROUND:]:  # every call needs an answer, but these never run
                why = f"Refused: at most {MAX_CALLS_PER_ROUND} tool calls per round"
                p["messages"].append({"role": "tool", "tool_call_id": c["id"], "name": c["name"], "content": why})
                p.setdefault("steps", []).append({"tool": c["name"], "args": c["args"], "result": why, "status": "refused", "ms": 0})
            if not calls: p["answer"] = out
            p["last"] = {"kind": "model", "round": p["rounds"], "text": shorten(out, STEP_CHARS), "limit_hit": hit,
                         "tool_calls": [{"name": c["name"], "args": c["args"]} for c in calls]}
            return {key: p}
        return fn

    if t == "agent_tool":
        by_name = {x.get("name"): x for x in d.get("tools") or [] if isinstance(x, dict)}
        def fn(state):
            p = copy.deepcopy(state.get(key) or {})
            if not p.get("pending"): return {}
            call = p["pending"][0]
            tool, args = by_name.get(call["name"]), call.get("args")
            bad = None if tool is None else arg_error(parameters(tool), args)
            decided = None
            got = child_result(resume, nid) if tool is not None and tool.get("source") == "workflow" else None
            if tool is not None and not bad and tool.get("approval") and got is None:  # a call that cannot run is not shown to an approver;
                # a child that finished ran after its approval
                decided = answer(resume, nid)
                if decided is None:
                    who = d.get("agent_label") or owner(node)
                    raise Interrupt(nid, ASK.get(ports.locale, ASK["en"]).format(agent=who, tool=call["name"], args=json.dumps(args, ensure_ascii=False, indent=2)),
                                    {"label": f"{who} › {call['name']}", "tool": call["name"], "arguments": args})
            p["pending"], t0 = p["pending"][1:], time.perf_counter()
            if tool is None:
                status, result = "error", f"Unknown tool {call['name']}: use one of {', '.join(sorted(n for n in by_name if n))}"
            elif bad:
                status, result = "error", f"Invalid arguments for {call['name']}: {bad}"
            elif decided is not None and decided.strip().lower() != APPROVED:
                status, result = "rejected", rejection(decided)
            elif got is not None:
                status, result = child_outcome(tool, got)
                if usage and got.get("usage"): usage(nid, got["usage"])  # the child's tokens and cost count on the Agent node
            elif tool.get("source") == "workflow":  # start the child run (once per call) and wait for it (DEC-0066)
                try:
                    if ports.start_child is None: raise RuntimeError("workflow tools need the run service")
                    call_key = f"{effects.key(nid) if effects else nid}#{call['id']}"
                    inp = {f: args[f] for f in field_list(tool.get("inputs")) if f in args}
                    cid = ports.start_child(call_key, tool.get("snapshot") or {}, tool.get("version"), inp,
                                            {"workflow_id": tool.get("workflow_id"), "tool": call["name"]})
                except Exception as e:
                    if getattr(e, "fenced", False): raise
                    status, result = "error", f"{FAILED}: {safe_error(e)}"
                else:
                    who = d.get("agent_label") or owner(node)
                    raise AwaitChild(nid, cid, {"label": f"{who} › {call['name']}", "tool": call["name"], "arguments": args,
                                                "workflow_id": tool.get("workflow_id")})
            else:
                try: status, result = "ok", text(run_tool(nid, tool, args, state, ports, effects))
                except Exception as e:
                    if getattr(e, "fenced", False): raise  # this worker lost the run
                    status, result = "error", f"{FAILED}: {safe_error(e)}"
            ms = round((time.perf_counter() - t0) * 1000, 2)
            p.setdefault("messages", []).append({"role": "tool", "tool_call_id": call["id"], "name": call["name"], "content": shorten(result, RESULT_CHARS)})
            step = {"tool": call["name"], "args": args, "result": shorten(result, STEP_CHARS), "status": status, "ms": ms,
                    **({"approval": APPROVED if status != "rejected" else REJECTED} if decided is not None else {})}
            p.setdefault("steps", []).append(step)
            p["last"] = {"kind": "tool", "round": p.get("rounds", 0), **step}
            return {key: p}
        return fn

    # agent_exit
    def fn(state):
        p = state.get(key) or {}
        out: Dict[str, Any] = {d["output_field"]: p.get("answer") or "", key: None}
        if d.get("steps_field"): out[d["steps_field"]] = p.get("steps") or []
        return out
    return fn
