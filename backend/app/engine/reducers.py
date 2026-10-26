"""State reducers (TASK-0011): how a node's output is combined with the current value of a state field.

replace (default) - the new value wins; two parallel branches writing the same field in one step is an error.
append            - list concatenation; a non-list output is appended as one item (collects parallel results).
merge             - shallow dict merge, later keys win.
add               - numeric sum.
The same functions back the LangGraph channels (compiler) and the runtime's own state tracking (trace events).
"""
from __future__ import annotations
from typing import Any, Callable, Dict, Optional
from .issues import Issue

REDUCERS = ("replace", "append", "merge", "add")
FIELD_TYPES = {"append": "list", "merge": "object", "add": ("number", "integer")}


def _append(a: Any, b: Any) -> list:
    a = [] if a is None else (a if isinstance(a, list) else [a])
    return a + (b if isinstance(b, list) else [] if b is None else [b])


def _merge(a: Any, b: Any) -> dict:
    return {**(a if isinstance(a, dict) else {}), **(b if isinstance(b, dict) else {})}


def _add(a: Any, b: Any):
    num = lambda x: x if isinstance(x, (int, float)) and not isinstance(x, bool) else 0
    return num(a) + num(b)


FUNCS: Dict[str, Callable[[Any, Any], Any]] = {"append": _append, "merge": _merge, "add": _add}


def reducer_of(field: dict) -> str:
    return field.get("reducer") or "replace"


def fn_of(field: dict) -> Optional[Callable[[Any, Any], Any]]:
    return FUNCS.get(reducer_of(field))


def field_errors(field: dict) -> list[str]:
    r = reducer_of(field); name = field.get("name")
    if r not in REDUCERS: return [Issue("REDUCER_UNKNOWN", field=name, reducer=r, reducers=", ".join(REDUCERS))]
    want = FIELD_TYPES.get(r)
    if want and field.get("type", "string") not in ((want,) if isinstance(want, str) else want):
        return [Issue("REDUCER_TYPE", field=name, reducer=r, types=want if isinstance(want, str) else " or ".join(want))]
    return []


def apply(state: Dict[str, Any], delta: Dict[str, Any], schema: list) -> Dict[str, Any]:
    """state + delta with the declared reducers (fields without one are replaced)."""
    funcs = {f["name"]: fn_of(f) for f in schema or [] if fn_of(f)}
    out = dict(state)
    for k, v in (delta or {}).items():
        out[k] = funcs[k](out.get(k), v) if k in funcs else v
    return out
