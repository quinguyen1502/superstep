"""Agent hand-offs (REQ-0078, DEC-0073): the model of the targets and the run limit (TASK-0179).

An Agent node lists the agents it may hand the conversation to in `handoffs`: [{target: <node id>, description}]. A
target is another Agent node of the same graph (the workflow, or the subgraph the node sits in); never the node
itself, and once per node. The workflow's `max_handoffs` (default 5, 0 to 20) bounds the hand-offs of one run.
The targets live in node data, not in edges, so the canvas draws its dashed links from them (decision 1).
"""
from __future__ import annotations
from typing import Any, Dict, List
from .issues import Issue

DEFAULT_MAX, MAX = 5, 20


def targets(d: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The node's hand-off entries that are objects with a target id."""
    return [h for h in (d.get("handoffs") or []) if isinstance(h, dict) and isinstance(h.get("target"), str) and h["target"]] \
        if isinstance(d.get("handoffs"), list) else []


def limit(wf: Dict[str, Any]) -> int:
    v = wf.get("max_handoffs", DEFAULT_MAX)
    return v if isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= MAX else DEFAULT_MAX


def limit_errors(wf: Dict[str, Any]) -> List[str]:
    v = wf.get("max_handoffs", DEFAULT_MAX)
    ok = isinstance(v, int) and not isinstance(v, bool) and 0 <= v <= MAX
    return [] if ok else [Issue("AGENT_HANDOFF_LIMIT", max=MAX)]


def errors(nid: str, d: Dict[str, Any], types: Dict[str, Any]) -> List[str]:
    """Each target must be another Agent node of this graph, listed once. `types`: node id -> type."""
    raw = d.get("handoffs")
    if raw is None: return []
    if not isinstance(raw, list): return [Issue("AGENT_HANDOFF_TARGET_INVALID", node=nid, target="?")]
    out, seen = [], set()
    for h in raw:
        t = h.get("target") if isinstance(h, dict) else None
        if not isinstance(t, str) or t == nid or types.get(t) != "agent" or t in seen:
            out.append(Issue("AGENT_HANDOFF_TARGET_INVALID", node=nid, target=str(t)[:64]))
        seen.add(t)
    return out


def links(nodes: List[Dict[str, Any]]) -> List[tuple]:
    """(source, target) of every listed hand-off, for reachability."""
    return [(n["id"], h["target"]) for n in nodes if n.get("type") == "agent" for h in targets(n.get("data") or {})]


def refusal(wf: Dict[str, Any]):
    """The first hand-off problem as (code, params), or None: saving refuses it (the server keeps no dangling target)."""
    nodes = [n for n in wf.get("nodes") or [] if isinstance(n, dict) and n.get("id")]
    types = {n["id"]: n.get("type") for n in nodes}
    for n in nodes:
        if n.get("type") == "agent":
            for i in errors(n["id"], n.get("data") or {}, types): return i.code, i.params
    for i in limit_errors(wf): return i.code, i.params
    return None
