"""`{{state.field}}` templating for prompts, URLs, bodies, queries and tool arguments (TASK-0044, DEC-0034).

A reference is `{{ state.<field>[.<key>|.<index>]... [| filter[(arg)]]... }}`:
- the path walks dicts by key and lists by index; anything missing gives None, which renders as ""
- filters run left to right; an argument is one quoted string or an integer
"""
from __future__ import annotations
import json, re
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Tuple
from ..core.errors import AppError
from .issues import Issue

_NAME = r"[A-Za-z_][A-Za-z0-9_]*"
_ARG = r"\"[^\"]*\"|'[^']*'|-?\d+"
_FILTER = rf"\|\s*{_NAME}\s*(?:\(\s*(?:{_ARG})\s*\))?\s*"
# group 1: field, group 2: `.a.0` path, group 3: `| f | g("x")` chain. The frontend copy is `lib/state-refs.ts`.
VAR_RE = re.compile(rf"\{{\{{\s*state\.({_NAME})((?:\.(?:{_NAME}|\d+))*)\s*((?:{_FILTER})*)\}}\}}")
_ONE_FILTER = re.compile(rf"\|\s*({_NAME})\s*(?:\(\s*({_ARG})\s*\))?\s*")


def _text(v: Any) -> str:
    return "" if v is None else v if isinstance(v, str) else json.dumps(v, ensure_ascii=False)


def _truncate(v: Any, n: Any) -> str:
    s = _text(v)
    return s if len(s) <= n else s[:max(n - 1, 0)] + "…"


# name -> (function(value, arg), argument kind: None = no argument, str or int = required)
FILTERS: Dict[str, Tuple[Callable[[Any, Any], Any], Optional[type]]] = {
    "upper": (lambda v, _: _text(v).upper(), None),
    "lower": (lambda v, _: _text(v).lower(), None),
    "trim": (lambda v, _: _text(v).strip(), None),
    "json": (lambda v, _: json.dumps(v, ensure_ascii=False), None),
    "length": (lambda v, _: len(v) if isinstance(v, (str, list, dict)) else 0, None),
    "first": (lambda v, _: v[0] if isinstance(v, (str, list)) and v else None, None),
    "last": (lambda v, _: v[-1] if isinstance(v, (str, list)) and v else None, None),
    "default": (lambda v, a: a if v is None or v == "" else v, str),
    "join": (lambda v, a: a.join(_text(x) for x in v) if isinstance(v, list) else _text(v), str),
    "truncate": (_truncate, int),
}


class Ref(NamedTuple):
    field: str
    path: List[str]
    filters: List[Tuple[str, Any]]  # (name, parsed argument or None)


def _arg(raw: Optional[str]) -> Any:
    if raw is None: return None
    return raw[1:-1] if raw[0] in "\"'" else int(raw)


def parse(m: re.Match) -> Ref:
    return Ref(m.group(1), [p for p in m.group(2).split(".") if p],
               [(f.group(1), _arg(f.group(2))) for f in _ONE_FILTER.finditer(m.group(3) or "")])


def refs(text: str) -> List[Ref]:
    return [parse(m) for m in VAR_RE.finditer(text or "")]


def ref_errors(ref: Ref) -> List[str]:
    """Problems with a reference's filters (unknown name, missing or wrong argument)."""
    out = []
    for name, arg in ref.filters:
        if name not in FILTERS: out.append(Issue("FILTER_UNKNOWN", filter=name)); continue
        kind = FILTERS[name][1]
        if kind is None and arg is not None: out.append(Issue("FILTER_NO_ARGUMENT", filter=name))
        elif kind is not None and not isinstance(arg, kind): out.append(Issue("FILTER_NEEDS_TEXT" if kind is str else "FILTER_NEEDS_NUMBER", filter=name))
    return out


def _walk(v: Any, path: List[str]) -> Any:
    for p in path:
        if isinstance(v, dict): v = v.get(p)
        elif isinstance(v, list) and p.isdigit() and int(p) < len(v): v = v[int(p)]
        else: return None
    return v


def value(ref: Ref, state: Dict[str, Any]) -> Any:
    if (bad := ref_errors(ref)): raise AppError("TEMPLATE_REF_INVALID", reason=bad[0])
    v = _walk(state.get(ref.field), ref.path)
    for name, arg in ref.filters: v = FILTERS[name][0](v, arg)
    return v


def render(template: str, state: Dict[str, Any], escape: Optional[Callable[[str], str]] = None) -> str:
    """`escape` (e.g. html.escape) is applied to each inserted value, never to the template's own text."""
    esc = escape or (lambda x: x)
    return VAR_RE.sub(lambda m: esc(_text(value(parse(m), state))), template or "")


def render_args(args: Any, state: Dict[str, Any]) -> Any:
    """Render templates inside tool arguments: a string that is exactly one reference keeps the value's type."""
    if isinstance(args, dict): return {k: render_args(v, state) for k, v in args.items()}
    if isinstance(args, list): return [render_args(v, state) for v in args]
    if isinstance(args, str):
        m = VAR_RE.fullmatch(args.strip())
        return value(parse(m), state) if m else render(args, state)
    return args
