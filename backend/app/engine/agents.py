"""Agent nodes (TASK-0116, REQ-0072, DEC-0063): the model picks and calls the tools the node allows, round after round,
until it answers.

An Agent node `A` is expanded before compilation, as subgraph nodes are, into ordinary LangGraph steps:
    A (entry: builds the conversation) → A/__model ⇄ a wave of A/__tool/1 .. A/__tool/8 → A/__join → A/__exit
A wave is one superstep (LangGraph Send): the calls run together, up to the cap, and the join puts their results back
in the model's order (DEC-0069). Each slot has its own ledger entry. The conversation lives in the hidden state field
`agent:A` (plain JSON): {messages, pending, rounds, limit_hit, steps, answer, last}. A slot writes `agent:A#<n>`, not
that object.

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
from langgraph.types import Send
from .effects import Effects, call_tool
from .errors import AwaitChild, Interrupt, ValidationError
from .issues import Issue
from .limits import safe_error
from .llm import call_agent
from .ports import Ports
from .state_schema import state_schema
from . import attachments, subgraphs
from .templating import refs, render
from .tools import PARAMETERS, TOOLS

PREFIX, SEP = "agent:", "/"
MODEL, TOOL, JOIN, EXIT, HANDOFF = "__model", "__tool", "__join", "__exit", "__handoff"
# hand-offs (REQ-0078, DEC-0073): the pending hand-off {from, to, reason, messages, last} and the run's count
HANDOFF_KEY, COUNT_KEY = PREFIX + "__handoff", PREFIX + "__handoffs"
START_INPUT, START_KEY = "__start_agent", PREFIX + "__start"  # a chat continues with the agent that answered last (TASK-0181)
NOT_RUN = "Not run: the conversation was handed off"
HANDOFF_NOTE = "The conversation was handed off to you by {source}.{reason} Continue it and answer the person yourself."
NO_MORE = "You cannot hand the conversation off again in this run: answer the person yourself."
TYPES = ("agent", "agent_model", "agent_tool", "agent_exit", "agent_join", "agent_handoff")
ROUTERS = ("agent_model", "agent_join", "agent_handoff")  # steps that pick the next step (they may loop)
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
    """`A` for `A/__tool`, `A/__tool/2` or `A/__join`. Approvals and test answers use the Agent node's id (TASK-0117)."""
    if not isinstance(nid, str): return None
    if nid.endswith(SEP + JOIN): return nid[:-(len(SEP) + len(JOIN))] or None
    head, _, rest = nid.rpartition(SEP + TOOL)
    if head and (rest == "" or (rest[:1] == SEP and rest[1:].isdigit())): return head
    return None


def slot_index(nid: str) -> int:
    """1 for `A/__tool/1`. A bare `A/__tool` is slot 1."""
    rest = nid.rpartition(SEP + TOOL)[2] if isinstance(nid, str) else ""
    return int(rest[1:]) if rest[:1] == SEP and rest[1:].isdigit() else 1


def slot_id(agent: str, n: int) -> str:
    return f"{agent}{SEP}{TOOL}{SEP}{n}"


def slot_channel(node: Dict[str, Any]) -> str:
    """State key a tool slot writes. Parallel slots must not share `agent:A`."""
    return f"{private(owner(node))}#{slot_index(node['id'])}"


def wave_size(data: Dict[str, Any]) -> int:
    """Calls of this round that start together. The node setting off forces one, whatever the env cap says."""
    if data.get("parallel_tool_calls") is False: return 1
    return config.agent_parallel_tools()


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


REASON = {"type": "object", "properties": {"reason": {"type": "string", "description": "Why the conversation is handed off"}}}


def handoff_specs(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The hand-off tools as the model sees them: `transfer_to_<target>` with an optional reason (TASK-0180)."""
    return [{"name": h["name"], "description": h.get("description") or f"Hand the conversation to {h['label']}", "parameters": REASON}
            for h in d.get("handoff_tools") or []]


def _handoff_tools(nid: str, d: Dict[str, Any], labels: Dict[str, str], taken: set) -> List[Dict[str, Any]]:
    """[{name, target, label, description}] for the node's valid targets; names are unique among its tools."""
    from . import handoffs
    out, used = [], set(taken)
    for h in handoffs.targets(d):
        t = h["target"]
        if t == nid or t not in labels: continue
        base = "transfer_to_" + (re.sub(r"[^A-Za-z0-9_-]+", "_", labels[t]).strip("_").lower() or re.sub(r"[^A-Za-z0-9_-]+", "_", t))
        base = base[:60]; name, i = base, 2
        while name in used: name, i = f"{base[:58]}_{i}", i + 1
        used.add(name)
        out.append({"name": name, "target": t, "label": labels[t], "description": str(h.get("description") or "")})
    return out


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
    from . import handoffs
    labels = {n["id"]: (n.get("data") or {}).get("label") or n["id"] for n in nodes if isinstance(n, dict) and n.get("type") == "agent"}
    cap = handoffs.limit(wf)
    for n in [n for n in nodes if isinstance(n, dict) and n.get("type") == "agent" and not (n.get("data") or {}).get("agent_expanded")]:
        a, d = n["id"], n.get("data") or {}
        label = d.get("label") or a
        n["data"] = {**d, "agent_expanded": True}
        # a cached step would skip its model or tool call (and its approval) on a run with the same state: only the
        # entry step keeps the node's cache and input fields; retry and timeout apply to each step
        inner = {k: v for k, v in d.items() if k not in ("label", "cache_ttl", "input_fields")}
        hand = _handoff_tools(a, d, labels, {t.get("name") for t in d.get("tools") or [] if isinstance(t, dict)})
        if hand: inner = {**inner, "handoff_tools": hand, "max_handoffs": cap}
        # a workflow tool's child snapshot is run by the tool step only: the other steps keep its state fields (the
        # parameter types), which keeps the checkpoint small
        lean = {**inner, "tools": [{**t, "snapshot": {"state": t["snapshot"].get("state") or []}}
                                   if isinstance(t, dict) and isinstance(t.get("snapshot"), dict) else t for t in d.get("tools") or []]}
        step = lambda suffix, typ, name, data: {"id": f"{a}{SEP}{suffix}", "type": typ, "position": n.get("position"),
                                                "data": {**data, "label": f"{label} › {name}", "agent_of": a, "agent_label": label}}
        n["data"] = {**n["data"], "tools": lean["tools"]} if "tools" in d else n["data"]
        slots = [step(f"{TOOL}{SEP}{i}", "agent_tool", "tool", inner) for i in range(1, MAX_CALLS_PER_ROUND + 1)]
        if hand: lean = {**lean, "handoff_tools": hand, "max_handoffs": cap}
        nodes += [step(MODEL, "agent_model", "model", lean), *slots, step(JOIN, "agent_join", "join", lean), step(EXIT, "agent_exit", "end", lean)]
        m, j, x = f"{a}{SEP}{MODEL}", f"{a}{SEP}{JOIN}", f"{a}{SEP}{EXIT}"
        edges[:] = [{**e, "source": x} if e.get("source") == a else e for e in edges]  # the agent's way out
        edges += [{"id": f"{a}{SEP}e-model", "source": a, "target": m},
                  {"id": f"{a}{SEP}e-done", "source": m, "target": x, "label": "done"},
                  {"id": f"{a}{SEP}e-back", "source": j, "target": m, "label": "model"}]
        if hand:  # a hand-off is its own step, then a jump to the target's entry (DEC-0073 decision 2)
            h = f"{a}{SEP}{HANDOFF}"
            nodes.append(step(HANDOFF, "agent_handoff", "hand-off", lean))
            edges += [{"id": f"{a}{SEP}e-handoff", "source": m, "target": h, "label": "handoff"}]
            edges += [{"id": f"{a}{SEP}e-to-{x['target']}", "source": h, "target": x["target"], "label": x["target"]} for x in hand]
        for i in range(1, MAX_CALLS_PER_ROUND + 1):  # the model reaches every slot (the router Sends only the wave)
            sid = slot_id(a, i)
            edges += [{"id": f"{a}{SEP}e-slot-{i}", "source": m, "target": sid},
                      {"id": f"{a}{SEP}e-join-{i}", "source": sid, "target": j}]
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
    """Extra LangGraph steps the Agent nodes may need. A round is a model call plus, at cap 1, a slot and a join per
    tool call. The last call without tools, the entry and the exit come on top."""
    from . import handoffs
    total, most, any_hand = 0, 0, False
    for n in wf.get("nodes", []):
        if isinstance(n, dict) and n.get("type") == "agent":
            r = (n.get("data") or {}).get("max_rounds", DEFAULT_ROUNDS)
            r = r if isinstance(r, int) and not isinstance(r, bool) and 1 <= r <= MAX_ROUNDS else DEFAULT_ROUNDS
            cost = r * (1 + 2 * MAX_CALLS_PER_ROUND) + 3
            total += cost; most = max(most, cost)
            any_hand = any_hand or bool(handoffs.targets(n.get("data") or {}))
    if any_hand: total += handoffs.limit(wf) * (most + 2)  # each hand-off may run an agent again (TASK-0180)
    return total


def router(node: Dict[str, Any]):
    """After the model: Send the first wave, or `done` when nothing is pending. After the join: Send the next wave,
    or back to `model`."""
    key, agent, data = private(owner(node)), owner(node), node.get("data") or {}
    back = "done" if node["type"] == "agent_model" else "model"
    if node["type"] == "agent_handoff":
        return lambda state: (state.get(HANDOFF_KEY) or {}).get("to")

    def route(state):
        if node["type"] == "agent_model" and (state.get(key) or {}).get("handoff"): return "handoff"
        pending = ((state.get(key) or {}).get("pending")) or []
        if not pending: return back
        n = min(len(pending), wave_size(data))
        return [Send(slot_id(agent, i), dict(state)) for i in range(1, n + 1)]
    return route


# ---- steps ------------------------------------------------------------------------------------

def answer(resume: Optional[Dict[str, Any]], nid: str) -> Optional[str]:
    """The approver's answer for this step, consumed once (as for a Human node) so a later call to the tool asks again.
    A wave keeps one answer per slot in `answers` (TASK-0158)."""
    if resume is None: return None
    bag = resume.get("answers")
    if isinstance(bag, dict) and nid in bag: return str(bag.pop(nid))
    if resume.get("node") == nid and "value" in resume and not isinstance(resume.get("value"), dict): return str(resume.pop("value"))
    return None


def child_result(resume: Optional[Dict[str, Any]], nid: str) -> Optional[Dict[str, Any]]:
    """The finished child run of a workflow tool call, consumed once: {child_run_id, status, output, error, usage}. The
    run service sends it as a dict; a person's answer is always text, so it can never pass for one (TASK-0134).
    A wave keeps one result per slot in `children` until every wait has settled (TASK-0158)."""
    if resume is None: return None
    bag = resume.get("children")
    if isinstance(bag, dict) and isinstance(bag.get(nid), dict) and "child_run_id" in bag[nid]: return bag.pop(nid)
    v = resume.get("value") if resume.get("node") == nid else None
    if isinstance(v, dict) and "child_run_id" in v: return resume.pop("value")
    return None


def _pause(effects: Optional[Effects], item: dict, exc: Exception) -> None:
    """Record the pause, then raise it. Parallel slots all record before the superstep stops (TASK-0158)."""
    if effects is not None: effects.hold(item)
    raise exc


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


def history(items, prompt: str) -> list:
    """The {role, content} messages of a history field, before the task prompt. A chat's conversation field ends with
    the current message (DEC-0052); when the prompt already carries it (e.g. `{{state.message}}`), that last item is
    left out so the model gets the message once, as the prompt (TASK-0214)."""
    msgs = [{"role": m["role"], "content": m["content"]} for m in items or []
            if isinstance(m, dict) and m.get("role") in ("user", "assistant") and isinstance(m.get("content"), str)]
    if msgs and msgs[-1]["role"] == "user" and msgs[-1]["content"].strip() in prompt: msgs.pop()
    return msgs


def node_fn(node: Dict[str, Any], resolve=None, usage=None, effects: Optional[Effects] = None, ports: Optional[Ports] = None,
            offline: bool = False, tokens: Optional[Callable[[str], Any]] = None, resume: Optional[Dict[str, Any]] = None) -> Callable[[dict], dict]:
    """tokens(nid) -> a TokenBuffer for the run stream, or None (engine/nodes.token_stream).
    resume: {"node", "value"} when the run continues after an approval (engine/runtime)."""
    ports = ports or Ports()
    t, d, nid = node["type"], node.get("data") or {}, node["id"]
    key = private(owner(node))

    if t == "agent":
        def fn(state):
            got = state.get(HANDOFF_KEY) if isinstance(state.get(HANDOFF_KEY), dict) else None
            got = got if got and got.get("to") == nid else None  # a hand-off to this agent (TASK-0180)
            system = render(d["system_prompt"], state) if d.get("system_prompt") else ""
            if got:
                why = f" Reason: {got['reason']}." if got.get("reason") else ""
                system = "\n\n".join(x for x in (system, HANDOFF_NOTE.format(source=got.get("from_label") or got.get("from"), reason=why)) if x)
            msgs = [{"role": "system", "content": system}] if system else []
            if got:  # the person's messages and the agents' replies, without tool traffic (DEC-0073 decision 3)
                msgs += [{"role": m["role"], "content": m["content"]} for m in got.get("messages") or []]
            prompt = render(d.get("prompt") or "", state)
            if not got:
                msgs += history(state.get(d["history_field"]) if d.get("history_field") else None, prompt)
            files = attachments.records(state, d)  # chat attachments (TASK-0176): records only, image bytes are read per call
            msgs.append({"role": "user", "content": prompt, **({"files": files} if files else {})})
            out = {key: {"messages": msgs, "pending": [], "rounds": 0, "limit_hit": False, "steps": [], "answer": None, "last": None}}
            if got: out[HANDOFF_KEY] = None
            return out
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
            hand = {h["name"]: h for h in d.get("handoff_tools") or []}
            can = bool(hand) and not hit and (state.get(COUNT_KEY) or 0) < d.get("max_handoffs", 5)
            if hand and not can and not hit and not p.get("no_more"):  # past the limit: the model is told to answer itself
                ms = p.setdefault("messages", [])
                if ms and ms[0].get("role") == "system": ms[0] = {**ms[0], "content": f"{ms[0]['content']}\n\n{NO_MORE}"}
                else: ms.insert(0, {"role": "system", "content": NO_MORE})
                p["no_more"] = True
            try:
                msgs = p.get("messages") or []
                extra = {"load": ports.attachment} if any(m.get("files") for m in msgs) else {}  # the file loader only when files are sent
                tools = None if hit else specs(d) + (handoff_specs(d) if can else [])
                out, calls = call_agent(msgs, tools, d.get("model") or "gpt-4o-mini", cred,
                                        (lambda u: usage(nid, u)) if usage else None, buf, mock=offline, locale=ports.locale,
                                        parallel=False if d.get("parallel_tool_calls") is False else None, **extra)
            finally:
                if buf: buf.flush()
            calls = [] if hit else [{"id": str(c.get("id") or f"call_{i}"), "name": str(c.get("name") or ""), "args": c.get("args")}
                                    for i, c in enumerate(calls)]
            if not hit: p["rounds"] = p.get("rounds", 0) + 1
            p["limit_hit"] = hit
            p.setdefault("messages", []).append({"role": "assistant", "content": out, **({"tool_calls": calls} if calls else {})})
            first = next((c for c in calls if c["name"] in hand), None) if can else None
            if first is not None:  # the hand-off wins: the other calls of the round are answered, not run (TASK-0180)
                h = hand[first["name"]]; args = first.get("args") if isinstance(first.get("args"), dict) else {}
                reason = str(args.get("reason") or "")[:500]
                for c in calls:
                    done = c is first
                    msg = f"Handed off to {h['label']}" if done else NOT_RUN
                    p["messages"].append({"role": "tool", "tool_call_id": c["id"], "name": c["name"], "content": msg})
                    if not done: p.setdefault("steps", []).append({"tool": c["name"], "args": c["args"], "result": NOT_RUN, "status": "not_run", "ms": 0})
                p["pending"], p["handoff"] = [], {"to": h["target"], "label": h["label"], "reason": reason, "tool": first["name"]}
                p["last"] = {"kind": "model", "round": p["rounds"], "text": shorten(out, STEP_CHARS), "limit_hit": False,
                             "tool_calls": [{"name": c["name"], "args": c["args"]} for c in calls]}
                return {key: p}
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
        index, channel = slot_index(nid), slot_channel(node)
        def fn(state):
            pending = ((state.get(key) or {}).get("pending")) or []
            if index > len(pending): return {}  # a slot the router did not Send
            call = pending[index - 1]
            tool, args = by_name.get(call["name"]), call.get("args")
            bad = None if tool is None else arg_error(parameters(tool), args)
            decided = None
            got = child_result(resume, nid) if tool is not None and tool.get("source") == "workflow" else None
            if tool is not None and not bad and tool.get("approval") and got is None:  # a call that cannot run is not shown to an approver;
                # a child that finished ran after its approval
                decided = answer(resume, nid)
                if decided is None:
                    who = d.get("agent_label") or owner(node)
                    prompt = ASK.get(ports.locale, ASK["en"]).format(agent=who, tool=call["name"], args=json.dumps(args, ensure_ascii=False, indent=2))
                    extra = {"label": f"{who} › {call['name']}", "tool": call["name"], "arguments": args}
                    _pause(effects, {"node": nid, "kind": "approval", "prompt": prompt, **extra}, Interrupt(nid, prompt, extra))
            t0 = time.perf_counter()
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
                    extra = {"label": f"{who} › {call['name']}", "tool": call["name"], "arguments": args,
                             "workflow_id": tool.get("workflow_id")}
                    _pause(effects, {"node": nid, "kind": "child", "run_id": cid, **extra}, AwaitChild(nid, cid, extra))
            else:
                try: status, result = "ok", text(run_tool(nid, tool, args, state, ports, effects))
                except Exception as e:
                    if getattr(e, "fenced", False): raise  # this worker lost the run
                    status, result = "error", f"{FAILED}: {safe_error(e)}"
            ms = round((time.perf_counter() - t0) * 1000, 2)
            step = {"tool": call["name"], "args": args, "result": shorten(result, STEP_CHARS), "status": status, "ms": ms,
                    **({"child_run_id": got["child_run_id"], "child_workflow_id": tool.get("workflow_id")} if got is not None else {}),
                    **({"approval": APPROVED if status != "rejected" else REJECTED} if decided is not None else {})}
            message = {"role": "tool", "tool_call_id": call["id"], "name": call["name"], "content": shorten(result, RESULT_CHARS)}
            # the join appends this onto the conversation, in the model's order, whatever order the slots finish in
            return {channel: {"index": index, "message": message, "step": step,
                              "last": {"kind": "tool", "round": (state.get(key) or {}).get("rounds", 0), **step}}}
        return fn

    if t == "agent_join":
        def fn(state):
            p = copy.deepcopy(state.get(key) or {})
            found, clear = [], {}
            for i in range(1, MAX_CALLS_PER_ROUND + 1):
                ch = f"{key}#{i}"
                slot = state.get(ch)
                if isinstance(slot, dict) and slot.get("message"): found.append(slot)
                clear[ch] = None  # a later, smaller wave must not see a previous slot
            for s in sorted(found, key=lambda s: s.get("index") or 0):
                p.setdefault("messages", []).append(s["message"])
                p.setdefault("steps", []).append(s["step"])
            if found: p["pending"] = (p.get("pending") or [])[len(found):]
            p["last"] = None
            return {key: p, **clear}
        return fn

    if t == "agent_handoff":
        def fn(state):
            p = state.get(key) or {}
            h = p.get("handoff") or {}
            carried = [{"role": m["role"], "content": m["content"]} for m in p.get("messages") or []
                       if isinstance(m, dict) and isinstance(m.get("content"), str) and m["content"]
                       and (m.get("role") == "user" or (m.get("role") == "assistant" and not m.get("tool_calls")))]
            src = d.get("agent_label") or owner(node)
            last = {"kind": "handoff", "from": owner(node), "from_label": src, "to": h.get("to"), "to_label": h.get("label"), "reason": h.get("reason") or ""}
            out: Dict[str, Any] = {key: None, COUNT_KEY: (state.get(COUNT_KEY) or 0) + 1,
                                   HANDOFF_KEY: {"from": owner(node), "from_label": src, "to": h.get("to"), "reason": h.get("reason") or "",
                                                 "messages": carried, "last": last}}
            if d.get("steps_field"): out[d["steps_field"]] = (p.get("steps") or []) + [{"tool": h.get("tool"), "args": {"reason": h.get("reason") or ""},
                                                                                       "result": f"Handed off to {h.get('label')}", "status": "handoff", "ms": 0}]
            return out
        return fn

    # agent_exit
    def fn(state):
        p = state.get(key) or {}
        out: Dict[str, Any] = {d["output_field"]: p.get("answer") or "", key: None}
        if d.get("steps_field"): out[d["steps_field"]] = p.get("steps") or []
        return out
    return fn
