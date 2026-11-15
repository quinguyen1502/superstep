"""Pure structural diff between two workflow JSON documents.

Nodes/edges are matched by id, state fields by name. Node position changes are reported as
`moved` (layout only) so they don't drown real changes.
"""
import json
from typing import Any


def _by(items, key) -> dict:
    return {i.get(key): i for i in (items or []) if isinstance(i, dict) and i.get(key) is not None}


def _fields(a: dict, b: dict, skip=()) -> list[str]:
    return sorted(k for k in set(a) | set(b) if k not in skip and a.get(k) != b.get(k))


def _section(a: list, b: list, key: str, skip=()) -> dict:
    A, B = _by(a, key), _by(b, key)
    changed, moved = [], []
    for k in sorted(set(A) & set(B), key=str):
        f = _fields(A[k], B[k], skip)
        if f: changed.append({"id": k, "fields": f, "before": {x: A[k].get(x) for x in f}, "after": {x: B[k].get(x) for x in f}})
        elif "position" in skip and A[k].get("position") != B[k].get("position"): moved.append(k)
    out: dict[str, Any] = {"added": [B[k] for k in sorted(set(B) - set(A), key=str)],
                           "removed": [A[k] for k in sorted(set(A) - set(B), key=str)], "changed": changed}
    if "position" in skip: out["moved"] = moved
    return out


def diff_workflows(a: dict, b: dict) -> dict:
    d = {"nodes": _section(a.get("nodes"), b.get("nodes"), "id", skip=("position",)),
         "edges": _section(a.get("edges"), b.get("edges"), "id"),
         "state": _section(a.get("state"), b.get("state"), "name"),
         "name": None if a.get("name") == b.get("name") else {"before": a.get("name"), "after": b.get("name")}}
    d["identical"] = d["name"] is None and not any(
        s[k] for s in (d["nodes"], d["edges"], d["state"]) for k in ("added", "removed", "changed", "moved") if k in s)
    return d


def same_content(a: dict, b: dict) -> bool:
    """True when two workflows would execute identically (name/positions don't matter)."""
    def core(w):
        nodes = [{k: v for k, v in n.items() if k != "position"} for n in (w.get("nodes") or []) if isinstance(n, dict)]
        key = lambda x: json.dumps(x, sort_keys=True, ensure_ascii=False)
        return sorted(map(key, nodes)), sorted(map(key, w.get("edges") or [])), key(w.get("state") or [])
    return core(a) == core(b)
