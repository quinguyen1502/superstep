"""Compile workflow JSON {nodes, edges, state} into a LangGraph StateGraph."""
from __future__ import annotations
import re, string
from typing import Annotated, Any, Dict, List, Optional, TypedDict
from langgraph.cache.memory import InMemoryCache
from langgraph.graph import StateGraph, START, END
from . import agents, foreach
from .errors import ValidationError
from .node_policy import add_node_kwargs, input_schema, limit, needs_cache
from .nodes import node_fn
from .reducers import fn_of
from .validator import validate

TYPE_MAP = {"string": str, "number": float, "integer": int, "boolean": bool, "object": dict, "list": list}


def pick_branch(value: str, labels: List[str]) -> Optional[str]:
    """Condition label for `value` (TASK-0039, REQ-0027), independent of label order: exact match, then case-insensitive
    after trimming spaces and punctuation, then the longest label found as a whole word. A tie between two longest
    whole-word labels is ambiguous: None, so the default edge (or an error) applies."""
    if value in labels: return value
    norm = lambda x: x.strip().strip(string.punctuation + " ").casefold()
    for k in labels:
        if norm(k) and norm(k) == norm(value): return k
    hits = [k for k in labels if norm(k) and re.search(rf"(?<!\w){re.escape(norm(k))}(?!\w)", value.casefold())]
    if not hits: return None
    best = max(len(norm(k)) for k in hits)
    top = [k for k in hits if len(norm(k)) == best]
    return top[0] if len(top) == 1 else None


def compile_workflow(wf: Dict[str, Any], resolve=None, usage=None, entry=None, resume=None, effects=None, checkpointer=None, ports=None):
    """entry: start the graph at this node (or these nodes, run in parallel) instead of Start (resuming a paused or
    recovered run, TASK-0006/0021). effects: idempotency keys + node-result ledger (TASK-0021).
    checkpointer: LangGraph saver, used by the runtime to observe superstep checkpoints."""
    entries = set([entry] if isinstance(entry, str) else (entry or []))
    errs = validate(wf)
    if errs:
        from .subgraphs import readable  # expanded subgraph nodes by label (TASK-0029)
        raise ValidationError(readable(errs, wf))
    def annotation(f):
        typ = TYPE_MAP.get(f.get("type", "string"), str); fn = fn_of(f)
        return Annotated[typ, fn] if fn else Optional[typ]  # reducer fields: LangGraph combines parallel writes (TASK-0011)
    ann = {f["name"]: annotation(f) for f in wf.get("state", [])}
    ann.update({foreach.cursor(n["id"]): Optional[int] for n in wf["nodes"] if n.get("type") == "foreach"})  # loop positions (TASK-0049)
    ann.update({agents.private(n["id"]): Optional[dict] for n in wf["nodes"] if n.get("type") == "agent"})  # agent conversations (TASK-0116)
    ann.update({agents.slot_channel(n): Optional[dict] for n in wf["nodes"] if n.get("type") == "agent_tool"})  # one wave's tool results (DEC-0069)
    State = TypedDict("State", ann, total=False)  # type: ignore
    g = StateGraph(State)
    nodes = {n["id"]: n for n in wf["nodes"] if n.get("type") != "note"}  # notes are canvas comments (REQ-0025)
    joins = {nid for nid, n in nodes.items() if n["type"] == "join"}
    for nid, n in nodes.items():
        fn = node_fn(n, resolve, usage, resume, effects, ports)
        if effects: fn = effects.wrap(n, fn)
        data = n.get("data") or {}
        timeout = data.get("timeout")
        if isinstance(timeout, (int, float)) and not isinstance(timeout, bool):
            fn = limit(fn, float(timeout), nid)
        kw = add_node_kwargs(data)
        if (schema := input_schema(data, ann)) is not None:
            kw["input_schema"] = schema
        g.add_node(nid, fn, **kw)
    for nid, n in nodes.items():
        out = [e for e in wf["edges"] if e["source"] == nid and e["target"] in nodes]
        if nid in entries or (not entries and n["type"] == "start"):
            g.add_edge(START, nid)
        if n["type"] == "end":
            g.add_edge(nid, END)
        elif n["type"] == "foreach":
            g.add_conditional_edges(nid, foreach.router(nid), {e["label"]: e["target"] for e in out})
        elif n["type"] in agents.ROUTERS:
            # unlabeled edges (a model step to its tool slots) exist so the validator can see the slots; Send picks them
            g.add_conditional_edges(nid, agents.router(n), {e["label"]: e["target"] for e in out if e.get("label")})
        elif n["type"] == "condition":
            field = n["data"]["field"]
            mapping = {e["label"]: e["target"] for e in out}
            default = n["data"].get("default") or ("default" if "default" in mapping else None)
            label = n["data"].get("label") or nid
            def router(state, field=field, mapping=mapping, default=default, nid=nid, label=label):
                raw = state.get(field)
                v = ("" if raw is None else str(raw).lower() if isinstance(raw, bool) else str(raw)).strip()
                if (k := pick_branch(v, list(mapping))) is not None: return k
                if default and default in mapping: return default
                raise ValueError(f"Condition '{label}' ({nid}): value {field}='{v[:100]}' matches no label {list(mapping)} and there is no default")
            g.add_conditional_edges(nid, router, mapping)
        else:
            for e in out:
                if e["target"] not in joins: g.add_edge(nid, e["target"])  # several edges = parallel branches (TASK-0011)
    for j in joins:  # fan-in: the Join runs once, after every incoming branch finished
        if j in entries: continue
        g.add_edge([e["source"] for e in wf["edges"] if e["target"] == j and e["source"] in nodes], j)
    cache = InMemoryCache() if needs_cache(list(nodes.values())) else None
    return g.compile(checkpointer=checkpointer, **({} if cache is None else {"cache": cache}))
