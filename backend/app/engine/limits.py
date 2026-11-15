"""Runtime limits, payload caps and error sanitising.

Layers of caps:
- TRACE_CAP (runtime.cap_payload, 16 000 JSON chars): per traced field (`input`/`delta`) so the
  timeline stays light. Over the cap -> {"_truncated": True, "size", "preview"}.
- EVENT_MAX_BYTES (256 KB): whole event as sent/stored; oversized fields (state, input, delta, ...)
  are replaced by truncation markers.
- RUN_MAX_BYTES (2 MB): all events of a stored run; middle events are dropped and replaced by a
  single {"type": "truncated", "dropped": n} event; final_state is capped to EVENT_MAX_BYTES.
"""
import json, re

from ..core.config import event_max, run_max, input_max, workflow_max, run_timeout  # noqa: F401 (re-exported)

def size(obj) -> int:
    return len(json.dumps(obj, ensure_ascii=False, default=str).encode())

def marker(obj, keep: int = 2000) -> dict:
    txt = json.dumps(obj, ensure_ascii=False, default=str)
    return {"_truncated": True, "size": len(txt.encode()), "preview": txt[:keep]}

def cap_event(ev: dict, limit: int | None = None) -> dict:
    """Return ev unchanged if it fits, else a copy whose largest fields are replaced by markers."""
    limit = limit or event_max()
    if size(ev) <= limit: return ev
    out = dict(ev)
    for k in sorted((k for k in out if k not in ("type", "node", "label", "node_type", "iteration", "ts", "run_id", "duration_ms", "usage")),
                    key=lambda k: -size(out[k])):
        out[k] = marker(out[k]); out["_truncated"] = True
        if size(out) <= limit: break
    return out

def cap_run(events: list, limit: int | None = None) -> list:
    """Keep the head and tail of a run's events within limit; mark the dropped middle."""
    limit = limit or run_max()
    if size(events) <= limit: return events
    head, tail, budget = [], [], limit - 200
    i, j = 0, len(events) - 1
    while i <= j:  # alternate head/tail so both start and end are kept
        for side in ("h", "t"):
            if i > j: break
            e = events[i] if side == "h" else events[j]
            s = size(e) + 2
            if s > budget: i = j + 1; break
            budget -= s
            if side == "h": head.append(e); i += 1
            else: tail.insert(0, e); j -= 1
    dropped = len(events) - len(head) - len(tail)
    return head + [{"type": "truncated", "dropped": dropped}] + tail

_SECRET_RES = [
    (re.compile(r"(sk|pk|rk)-[A-Za-z0-9_\-]{8,}"), r"\1-***"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9._\-]+"), r"\1***"),
    (re.compile(r"(?i)((?:api[_-]?key|token|secret|password|key)=)[^&\s'\"]+"), r"\1***"),
]

def safe_error(e: BaseException, limit: int = 500) -> str:
    """One-line, secret-redacted error message: no stack traces, capped length."""
    from ..core.errors import AppError  # AppError messages are already user-facing (a demo DEMO_NODE_DISABLED): no class prefix
    msg = (str(e) if isinstance(e, AppError) else f"{type(e).__name__}: {e}").strip()
    msg = msg.splitlines()[0] if msg else type(e).__name__
    for rx, rep in _SECRET_RES: msg = rx.sub(rep, msg)
    return msg[:limit] + ("…" if len(msg) > limit else "")
