"""Agent nodes (TASK-0116, REQ-0072, DEC-0063): the model picks and calls the tools the node allows, round after round,
until it answers.

An Agent node `A` is expanded before compilation, as subgraph nodes are, into ordinary LangGraph steps:
    A (entry: builds the conversation) → A/__model (one model call) ⇄ A/__tool (one tool call) → A/__exit (the answer)
so every model call and every tool call checkpoints, recovers and uses the side-effect ledger on its own: a pause, a
crash or a restart repeats at most the step that had not finished. The conversation lives in the hidden state field
`agent:A` (plain JSON): {messages, pending, rounds, limit_hit, steps, answer, last}.

Node data: credential_id, model, system_prompt, prompt, output_field, steps_field?, history_field?, max_rounds and
`tools`, each {name, description, source: mcp | http | builtin | knowledge, approval?} plus its source's settings:
  mcp: server_id, tool, parameters (the server's input schema)    builtin: function (engine/tools.py)
  knowledge: knowledge_base_id, top_k                               http: method, url, body, parameters
HTTP templates read the model's arguments as `{{state.args.<name>}}`; without a body, POST/PUT/PATCH send the
arguments as JSON, and a GET whose URL does not use them gets them as query parameters.
"""
from __future__ import annotations
import copy, json, re, time
from typing import Any, Callable, Dict, List, Optional
from urllib.parse import urlencode
from ..core import config
from ..core.errors import AppError
from .effects import Effects, call_tool
from .limits import safe_error
from .llm import call_agent
from .ports import Ports
from .templating import refs, render
from .tools import PARAMETERS, TOOLS

PREFIX, SEP = "agent:", "/"
MODEL, TOOL, EXIT = "__model", "__tool", "__exit"
TYPES = ("agent", "agent_model", "agent_tool", "agent_exit")
ROUTERS = ("agent_model", "agent_tool")  # steps that pick the next step (they may loop)
SOURCES = ("mcp", "http", "builtin", "knowledge")
DEFAULT_ROUNDS, MAX_ROUNDS, MAX_CALLS_PER_ROUND = 5, 25, 8
RESULT_CHARS = 8000  # a tool result goes back to the model shortened to this
STEP_CHARS = 2000    # ... and into the steps field / trace shortened to this
NAME_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
METHODS = ("GET", "POST", "PUT", "PATCH", "DELETE")
QUERY = {"type": "object", "properties": {"query": {"type": "string", "description": "What to search for"}}, "required": ["query"]}
JSON_TYPES = {"string": str, "number": (int, float), "integer": int, "boolean": bool, "array": list, "object": dict}


def private(nid: str) -> str: return PREFIX + nid


def visible(state: Dict[str, Any]) -> Dict[str, Any]:
    """State without the agents' conversations (the run's output, the trace)."""
    return {k: v for k, v in state.items() if not k.startswith(PREFIX)}


def owner(node: Dict[str, Any]) -> str:
    """The Agent node an expanded step belongs to."""
    return (node.get("data") or {}).get("agent_of") or node["id"]


def step_of(delta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """What an agent step did, for its `node_finished` event (the delta itself leaves the conversation out)."""
    return next((v["last"] for k, v in delta.items() if k.startswith(PREFIX) and isinstance(v, dict) and v.get("last") is not None), None)


# ---- tools ------------------------------------------------------------------------------------

def parameters(t: Dict[str, Any]) -> Dict[str, Any]:
    src = t.get("source")
    if src == "knowledge": return QUERY
    if src == "builtin": return PARAMETERS.get(t.get("function") or "") or {"type": "object", "properties": {}}
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
    if not str(d.get("prompt") or "").strip(): errs.append(f"Agent node {nid}: the task prompt is missing")
    r = d.get("max_rounds", DEFAULT_ROUNDS)
    if not isinstance(r, int) or isinstance(r, bool) or not 1 <= r <= MAX_ROUNDS: errs.append(f"Agent node {nid}: max rounds must be 1-{MAX_ROUNDS}")
    for key, want in (("steps_field", "list"), ("history_field", "list")):
        f = d.get(key)
        if f and types and f not in types: errs.append(f"Agent node {nid}: {key} '{f}' is not in the state")
        elif f and types and types[f] != want: errs.append(f"Agent node {nid}: {key} '{f}' must be a list field")
    tools = d.get("tools")
    if not isinstance(tools, list) or not tools: return errs + [f"Agent node {nid}: add at least one tool"]
    seen = set()
    for i, t in enumerate(tools, 1):
        if not isinstance(t, dict): errs.append(f"Agent node {nid}: tool {i} is not an object"); continue
        name, src = t.get("name") or "", t.get("source")
        who = f"Agent node {nid}: tool {name or i}"
        if not NAME_RE.match(name): errs.append(f"{who}: the name must be 1-64 letters, digits, _ or -")
        elif name in seen: errs.append(f"Agent node {nid}: two tools are named {name}")
        seen.add(name)
        if src not in SOURCES: errs.append(f"{who}: unknown source '{src}'"); continue
        if src == "mcp" and not (t.get("server_id") and t.get("tool")): errs.append(f"{who}: choose an MCP server and tool")
        if src == "builtin" and t.get("function") not in TOOLS: errs.append(f"{who}: function '{t.get('function')}' is not registered")
        if src == "knowledge":
            if not t.get("knowledge_base_id"): errs.append(f"{who}: choose a knowledge base")
            k = t.get("top_k", 4)
            if not isinstance(k, int) or isinstance(k, bool) or not 1 <= k <= 20: errs.append(f"{who}: top_k must be 1-20")
        if src == "http":
            if not t.get("url"): errs.append(f"{who}: URL is missing")
            if (t.get("method") or "GET").upper() not in METHODS: errs.append(f"{who}: method must be one of {', '.join(METHODS)}")
        p = t.get("parameters")
        if p is not None and (not isinstance(p, dict) or not isinstance(p.get("properties", {}), dict) or p.get("type", "object") != "object"):
            errs.append(f"{who}: parameters must be a JSON Schema object with properties")
    return errs


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
        inner = {k: v for k, v in d.items() if k not in ("label", "cache", "input_fields")}
        step = lambda suffix, typ, name: {"id": f"{a}{SEP}{suffix}", "type": typ, "position": n.get("position"),
                                          "data": {**inner, "label": f"{label} › {name}", "agent_of": a}}
        nodes += [step(MODEL, "agent_model", "model"), step(TOOL, "agent_tool", "tool"), step(EXIT, "agent_exit", "end")]
        m, t, x = f"{a}{SEP}{MODEL}", f"{a}{SEP}{TOOL}", f"{a}{SEP}{EXIT}"
        edges[:] = [{**e, "source": x} if e.get("source") == a else e for e in edges]  # the agent's way out
        edges += [{"id": f"{a}{SEP}e-model", "source": a, "target": m},
                  {"id": f"{a}{SEP}e-call", "source": m, "target": t, "label": "tool"},
                  {"id": f"{a}{SEP}e-done", "source": m, "target": x, "label": "done"},
                  {"id": f"{a}{SEP}e-next", "source": t, "target": t, "label": "tool"},
                  {"id": f"{a}{SEP}e-back", "source": t, "target": m, "label": "model"}]
    out["edges"] = edges
    return out


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

def node_fn(node: Dict[str, Any], resolve=None, usage=None, effects: Optional[Effects] = None, ports: Optional[Ports] = None,
            offline: bool = False, tokens: Optional[Callable[[str], Any]] = None) -> Callable[[dict], dict]:
    """tokens(nid) -> a TokenBuffer for the run stream, or None (engine/nodes.token_stream)."""
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
            call, p["pending"] = p["pending"][0], p["pending"][1:]
            tool, args, t0 = by_name.get(call["name"]), call.get("args"), time.perf_counter()
            if tool is None:
                status, result = "error", f"Unknown tool {call['name']}: use one of {', '.join(sorted(n for n in by_name if n))}"
            elif (bad := arg_error(parameters(tool), args)):
                status, result = "error", f"Invalid arguments for {call['name']}: {bad}"
            else:
                try: status, result = "ok", text(run_tool(nid, tool, args, state, ports, effects))
                except Exception as e:
                    if getattr(e, "fenced", False): raise  # this worker lost the run
                    status, result = "error", f"The tool failed: {safe_error(e)}"
            ms = round((time.perf_counter() - t0) * 1000, 2)
            p.setdefault("messages", []).append({"role": "tool", "tool_call_id": call["id"], "name": call["name"], "content": shorten(result, RESULT_CHARS)})
            step = {"tool": call["name"], "args": args, "result": shorten(result, STEP_CHARS), "status": status, "ms": ms}
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
