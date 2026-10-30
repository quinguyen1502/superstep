"""Subgraph nodes (TASK-0011): a node that runs another saved workflow.

The child workflow is expanded inline before validation and compilation, so its nodes are ordinary nodes of the run:
they emit their own trace events, pause at Human nodes, checkpoint, recover and use the side-effect ledger exactly like
top-level nodes. Ids are prefixed with the subgraph node id (`sub/inner`); labels with its label (`Sub › Inner`).

Wiring: the subgraph node stays as a pass-through entry and connects to the child Start's targets; every child End
becomes one pass-through exit node `sub/__exit` that carries the subgraph node's outgoing edges.
State: shared by field name. Child fields missing in the parent are added; the same name must have the same type.
References are resolved by `load(workflow_id) -> dict | None` (the service binds it to workflows the user may read).

Agent nodes may call other workflows as tools (REQ-0073, DEC-0066). Those are not expanded here (a call is a child run),
but `check` follows them too, so cycles and depth count subgraphs and workflow tools together.
"""
from __future__ import annotations
import copy
from typing import Any, Callable, Dict, List, Optional, Tuple
from .errors import ValidationError
from .issues import Issue

MAX_DEPTH = 5
SEP, EXIT = "/", "__exit"
Loader = Callable[[str], Optional[Dict[str, Any]]]


def refs(wf: Dict[str, Any]) -> List[Tuple[str, str]]:
    """(node id, referenced workflow id) of the subgraph nodes of one workflow (not recursive)."""
    return [(n["id"], (n.get("data") or {}).get("workflow_id") or "") for n in wf.get("nodes", [])
            if isinstance(n, dict) and n.get("type") == "subgraph" and not (n.get("data") or {}).get("subgraph_of")]  # not yet expanded


def has_subgraphs(wf: Dict[str, Any]) -> bool: return bool(refs(wf))


def tool_refs(wf: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    """(Agent node id, tool settings) of the Agent nodes' workflow tools (not recursive; the expanded steps are skipped)."""
    return [(n["id"], t) for n in wf.get("nodes", []) if isinstance(n, dict) and n.get("type") == "agent"
            for t in (n.get("data") or {}).get("tools") or [] if isinstance(t, dict) and t.get("source") == "workflow"]


def all_refs(wf: Dict[str, Any]) -> List[Tuple[str, str]]:
    """(node id, referenced workflow id) of subgraph nodes and workflow tools: the workflows this one depends on."""
    return refs(wf) + [(nid, t.get("workflow_id") or "") for nid, t in tool_refs(wf)]


def check(wf: Dict[str, Any], load: Loader, self_id: Optional[str] = None) -> List[str]:
    """Reference errors without expanding: missing workflow, cycle, too deep, and a workflow tool's unknown fields. Used
    when saving and planning a run."""
    errs: List[str] = []
    def walk(w, stack, depth):
        for nid, ref in refs(w):
            if not ref: errs.append(Issue("SUBGRAPH_WORKFLOW_MISSING", node=nid)); continue
            if ref in stack: errs.append(Issue("SUBGRAPH_CYCLE", node=nid, workflow=ref, chain=" → ".join(stack + [ref]))); continue
            if depth >= MAX_DEPTH: errs.append(Issue("SUBGRAPH_TOO_DEEP", node=nid, max=MAX_DEPTH)); continue
            child = load(ref)
            if child is None: errs.append(Issue("SUBGRAPH_NOT_FOUND", node=nid, workflow=ref)); continue
            if child.get("source"): errs.append(Issue("SUBGRAPH_IMPORTED", node=nid)); continue
            walk(child, stack + [ref], depth + 1)
        for nid, t in tool_refs(w):
            ref, who = t.get("workflow_id") or "", {"node": nid, "tool": t.get("name") or "?"}
            if not ref: continue  # the validator reports AGENT_TOOL_WORKFLOW
            if ref in stack: errs.append(Issue("WORKFLOW_TOOL_CYCLE", **who, workflow=ref, chain=" → ".join(stack + [ref]))); continue
            if depth >= MAX_DEPTH: errs.append(Issue("WORKFLOW_TOOL_TOO_DEEP", **who, max=MAX_DEPTH)); continue
            child = load(ref)
            if child is None: errs.append(Issue("WORKFLOW_TOOL_NOT_FOUND", **who, workflow=ref)); continue
            if child.get("source"): errs.append(Issue("WORKFLOW_TOOL_IMPORTED", **who)); continue
            names = {f.get("name") for f in child.get("state") or [] if isinstance(f, dict)}
            for key, code in (("inputs", "WORKFLOW_TOOL_INPUT_UNKNOWN"), ("outputs", "WORKFLOW_TOOL_OUTPUT_UNKNOWN")):
                want = t.get(key) if isinstance(t.get(key), list) else []  # other shapes: AGENT_TOOL_INPUTS / _OUTPUTS
                errs.extend(Issue(code, **who, field=f) for f in want if isinstance(f, str) and f not in names)
            walk(child, stack + [ref], depth + 1)
    walk(wf, [self_id] if self_id else [], 0)
    return errs


def _merge_state(parent: list, child: list, nid: str, errs: List[str]) -> list:
    out = list(parent); known = {f["name"]: f for f in parent}
    for f in child:
        p = known.get(f["name"])
        if p is None: out.append(dict(f)); known[f["name"]] = f
        elif p.get("type", "string") != f.get("type", "string"):
            errs.append(Issue("SUBGRAPH_FIELD_TYPE", node=nid, field=f["name"], child_type=f.get("type", "string"), parent_type=p.get("type", "string")))
    return out


def validate_with(wf: Dict[str, Any], load: Loader, self_id: Optional[str] = None) -> List[str]:
    """Save-time validation: reference errors, else the expanded graph's errors (child fields count as known)."""
    from .validator import validate
    if not has_subgraphs(wf) and not tool_refs(wf): return validate(wf)
    errs = check(wf, load, self_id)
    if errs: return validate(wf) + errs
    try: x = expand(wf, load, self_id)
    except ValidationError as e: return e.errors
    return readable(validate(x), x)


def readable(errors: List[str], expanded: Dict[str, Any]) -> List[str]:
    """Name nodes that came from a subgraph by their labels (`"Sub › Inner"`) instead of internal ids (`sub/inner`)."""
    import re
    names = {n["id"]: (n.get("data") or {}).get("label") or n["id"] for n in expanded.get("nodes", []) if SEP in str(n.get("id"))}
    if not names: return errors
    pat = re.compile(r"(?<![\w/])(" + "|".join(re.escape(i) for i in sorted(names, key=len, reverse=True)) + r")(?: \([^)]*\))?(?![\w/])")
    name = lambda text: pat.sub(lambda m: f'"{names[m.group(1)]}"', text)
    return [Issue(e.code, name(e), **{k: name(v) if isinstance(v, str) else v for k, v in e.params.items()})
            if isinstance(e, Issue) else name(e) for e in errors]


def expand(wf: Dict[str, Any], load: Loader, self_id: Optional[str] = None) -> Dict[str, Any]:
    """The workflow with every subgraph node replaced by its child's nodes (recursively). Raises ValidationError."""
    if not has_subgraphs(wf): return wf
    errs = check(wf, load, self_id)
    if errs: raise ValidationError(errs)
    out = copy.deepcopy(wf)
    for _ in range(MAX_DEPTH + 1):  # one level per pass; check() bounded the depth
        if not has_subgraphs(out): break
        out = _expand_once(out, load, errs)
        if errs: raise ValidationError(errs)
    return out


def _expand_once(wf: Dict[str, Any], load: Loader, errs: List[str]) -> Dict[str, Any]:
    nodes, edges, state = list(wf["nodes"]), list(wf["edges"]), list(wf.get("state") or [])
    for nid, ref in refs(wf):
        child = load(ref) or {"nodes": [], "edges": []}
        sub = next(n for n in nodes if n["id"] == nid); label = (sub.get("data") or {}).get("label") or nid
        cn = {n["id"]: n for n in child.get("nodes", [])}
        start = next((i for i, n in cn.items() if n.get("type") == "start"), None)
        ends = {i for i, n in cn.items() if n.get("type") == "end"}
        if start is None or not ends: errs.append(Issue("SUBGRAPH_START_END", node=nid, workflow=ref)); continue
        exit_id = f"{nid}{SEP}{EXIT}"
        pid = lambda i: nid if i == start else exit_id if i in ends else f"{nid}{SEP}{i}"
        sub["data"] = {**sub.get("data", {}), "subgraph_of": ref}
        for i, n in cn.items():
            if i == start or i in ends: continue
            d = dict(n.get("data") or {}); d["label"] = f"{label} › {d.get('label') or i}"
            if isinstance(d.get("handoffs"), list):  # hand-off targets stay inside the subgraph (TASK-0180)
                d["handoffs"] = [{**h, "target": pid(h["target"])} if isinstance(h, dict) and h.get("target") in cn else h for h in d["handoffs"]]
            nodes.append({**n, "id": pid(i), "data": d})
        nodes.append({"id": exit_id, "type": "subgraph_exit", "position": sub.get("position"), "data": {"label": f"{label} › end"}})
        edges = [{**e, "source": exit_id} if e["source"] == nid else e for e in edges]  # the subgraph's way out
        for e in child.get("edges", []):
            edges.append({**e, "id": f"{nid}{SEP}{e.get('id')}", "source": pid(e["source"]), "target": pid(e["target"])})
        state = _merge_state(state, child.get("state") or [], nid, errs)
    return {**wf, "nodes": nodes, "edges": edges, "state": state}
