"""Node executors: build the LangGraph node function for each node type."""
from __future__ import annotations
from typing import Any, Callable, Dict, Optional
from urllib.parse import unquote, urlsplit
import httpx
from ..core import config
from ..core.errors import AppError
from ..core.net import pinned_request, public_address
from . import agents, code_languages, code_runtime, decisions, emails, foreach
from .effects import Effects, call_tool
from .errors import Interrupt
from .llm import LLMError, TokenBuffer, call_llm
from .ports import Ports
from .templating import render, render_args
from .tools import TOOLS
from .usage import UsageSink


Resolver = Callable[[str], Dict[str, Any]]


def token_stream(nid: str) -> Optional[TokenBuffer]:
    """Live LLM text for the run stream (TASK-0030): LangGraph `custom` stream mode, None outside a streamed run."""
    try: from langgraph.config import get_stream_writer; write = get_stream_writer()
    except Exception: return None
    return TokenBuffer(lambda delta: write({"node": nid, "delta": delta}))


def code_call(nid: str, d: Dict[str, Any], state: Dict[str, Any], ports: Ports) -> Any:
    """Tool node Code mode (TASK-0053): main(state) in the sandbox. What it printed goes to the trace (`code_output`)."""
    if config.code_runtime() == "subprocess" and ports.code_audit is not None and code_runtime.claim_first_unisolated_call():
        try: ports.code_audit()  # first unisolated call since this process started (TASK-0056)
        except Exception: pass
    res = code_runtime.run_code(d.get("code") or "", dict(state), node=nid, timeout=d.get("timeout"), cancelled=ports.cancelled,
                                language=code_languages.language_of(d))
    try: from langgraph.config import get_stream_writer; get_stream_writer()({"node": nid, "code_output": res.trace()})
    except Exception: pass  # outside a streamed run
    return res.value


def http_call(nid: str, d: Dict[str, Any], state: Dict[str, Any], extra: Dict[str, str]) -> Any:
    """HTTP Tool request (TASK-0039, REQ-0027): public http(s) addresses only unless STUDIO_HTTP_TOOL_ALLOW_PRIVATE=1.
    The host is resolved once and the request connects to that checked IP; redirects are never followed."""
    return http_send(nid, d.get("method", "GET"), render(d.get("url", ""), state), render(d.get("body", ""), state), extra)


def http_send(nid: str, method: str, url: str, body: str, extra: Dict[str, str]) -> Any:
    """The request of an HTTP Tool node or an Agent node's HTTP tool, with its URL and body already rendered."""
    url, ip = public_address(url, config.http_tool_allow_private(), "HTTP_TOOL_URL_BLOCKED", node=nid)
    target, headers, ext = pinned_request(url, ip)
    u = urlsplit(url); auth = (unquote(u.username), unquote(u.password or "")) if u.username else None  # user:pass@ in the URL
    with httpx.Client(timeout=config.http_tool_timeout(), follow_redirects=False) as c:
        r = c.send(c.build_request(method, target, content=body.encode() if body else None,
                                   headers={"Content-Type": "application/json", **extra, **headers}, extensions=ext), auth=auth)
    try: return r.json()
    except Exception: return r.text


def node_fn(node: Dict[str, Any], resolve: Optional[Resolver] = None, usage: Optional[UsageSink] = None,
            resume: Optional[Dict[str, Any]] = None, effects: Optional[Effects] = None, ports: Optional[Ports] = None):
    """resolve(credential_id) -> decrypted credential; bound to the run's user by the service layer.
    usage(node_id, record): optional sink for LLM token usage (TASK-0010).
    effects: idempotency keys for side effects (TASK-0021): HTTP Tool nodes send `Idempotency-Key`.
    ports: user-bound services (knowledge base search, MCP calls; TASK-0012/0013)."""
    ports = ports or Ports()
    t, d = node["type"], node.get("data", {})
    offline = ports.mock_models or config.demo_mode()  # the public demo never calls a model provider
    if t == "llm":
        def fn(state):
            cred = None
            if d.get("credential_id") and not offline:
                if resolve is None: raise LLMError("Node uses a credential but no resolver is available")
                cred = resolve(d["credential_id"])
            report = (lambda u: usage(node["id"], u)) if usage else None
            tokens = token_stream(node["id"])
            try: return {d["output_field"]: call_llm(render(d.get("prompt", ""), state), d.get("model", "gpt-4o-mini"), cred, report, tokens,
                                                     mock=offline, locale=ports.locale)}
            finally:
                if tokens: tokens.flush()
    elif t == "human":
        def fn(state):
            # resume = {"node", "value"} for the node the run paused at; consumed once so a loop back here pauses again.
            # A wave keeps one answer per node in `answers` (TASK-0158).
            bag = (resume or {}).get("answers")
            if isinstance(bag, dict) and node["id"] in bag:
                return {d["output_field"]: bag.pop(node["id"])}
            if resume is not None and resume.get("node") == node["id"] and "value" in resume:
                return {d["output_field"]: resume.pop("value")}
            prompt = render(d.get("prompt", ""), state)
            if effects is not None:
                effects.hold({"node": node["id"], "kind": "approval", "prompt": prompt, "label": d.get("label") or node["id"]})
            raise Interrupt(node["id"], prompt)
    elif t == "tool":
        def fn(state):
            if d.get("mode") == "http":
                if config.demo_mode(): raise AppError("DEMO_NODE_DISABLED", node="HTTP Tool")
                res = http_call(node["id"], d, state, effects.headers(node["id"]) if effects else {})
            elif d.get("mode") == "code":
                res = code_call(node["id"], d, state, ports)
            else:
                res = call_tool(TOOLS[d["function"]], state, effects.key(node["id"]) if effects else None, ports.locale)
            return {d["output_field"]: res}
    elif t == "retriever":
        def fn(state):
            if ports.retrieve is None: raise RuntimeError("Retriever nodes need a knowledge base service")
            query = render(d.get("query", ""), state)
            return {d["output_field"]: ports.retrieve(d["knowledge_base_id"], query, int(d.get("top_k") or 4))}
    elif t == "mcp":
        def fn(state):
            if ports.mcp_call is None: raise RuntimeError("MCP nodes need the MCP service")
            return {d["output_field"]: ports.mcp_call(d["server_id"], d["tool"], render_args(d.get("arguments") or {}, state))}
    elif t == "decision":
        fn = decisions.node_fn(node, resolve, usage, offline=offline)
    elif t == "foreach":
        fn = foreach.node_fn(node)
    elif t in agents.TYPES:  # an Agent node and its expanded steps (TASK-0116, DEC-0063)
        fn = agents.node_fn(node, resolve, usage, effects, ports, offline, token_stream, resume)
    elif t == "email" and config.demo_mode():
        def fn(state): raise AppError("DEMO_NODE_DISABLED", node="Send email")
    elif t == "email":
        fn = emails.node_fn(node, resolve, (lambda: effects.key(node["id"])) if effects else (lambda: None), ports)
    else:  # start, condition, end, join, subgraph entry/exit -> passthrough
        def fn(state):
            return {}
    return fn
