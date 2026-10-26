"""Per-node retry, cache, and timeout taken from the canvas and applied at compile time.

`retry` and `cache_ttl` become `RetryPolicy` and `CachePolicy` on `StateGraph.add_node`.
`timeout` does not: LangGraph only cancels async nodes, and these node bodies block
(LLM, HTTP, tools). A daemon thread is joined for the given seconds, then the attempt
raises `NodeTimeoutError`, which a retry policy still treats as retryable. The thread
may finish later; the run does not wait for it.
"""
from __future__ import annotations
import contextvars, threading
from typing import Any, Callable, Dict, List, Optional, TypedDict
from langgraph.errors import NodeTimeoutError
from .issues import Issue
from langgraph.types import CachePolicy, RetryPolicy
from .errors import Interrupt

RUNTIME_TYPES = ("llm", "tool", "retriever", "mcp", "human", "decision")
ATTEMPTS = (1, 10)
WAIT = (0, 120)          # seconds, exclusive minimum
TIMEOUT = (0, 3600)
CACHE_TTL = (1, 86400)


def _num(value: Any) -> Optional[float]:
    if isinstance(value, bool) or not isinstance(value, (int, float)): return None
    return float(value)


def errors(nid: str, data: Dict[str, Any], fields: Optional[set] = None) -> List[str]:
    """Human-readable problems with this node's execution settings. Empty when unset or valid."""
    out: List[str] = []
    names = data.get("input_fields")
    if names not in (None, []):
        if (not isinstance(names, list) or not all(isinstance(n, str) and n for n in names)
                or len(names) != len(set(names))):
            out.append(Issue("INPUT_FIELDS_INVALID", node=nid))
        elif fields is not None:
            unknown = [n for n in names if n not in fields]
            if unknown:
                out.append(Issue("INPUT_FIELD_UNKNOWN", node=nid, field=unknown[0]))
    retry = data.get("retry")
    if retry not in (None, {}):
        if not isinstance(retry, dict):
            out.append(Issue("RETRY_INVALID", node=nid))
        else:
            attempts, wait = retry.get("max_attempts"), retry.get("initial_interval")
            if isinstance(attempts, bool) or not isinstance(attempts, int) or not ATTEMPTS[0] <= attempts <= ATTEMPTS[1]:
                out.append(Issue("RETRY_ATTEMPTS", node=nid, min=ATTEMPTS[0], max=ATTEMPTS[1]))
            if wait is not None and ((n := _num(wait)) is None or not WAIT[0] < n <= WAIT[1]):
                out.append(Issue("RETRY_WAIT", node=nid, max=WAIT[1]))
    timeout = data.get("timeout")
    if timeout is not None and ((n := _num(timeout)) is None or not TIMEOUT[0] < n <= TIMEOUT[1]):
        out.append(Issue("TIMEOUT_INVALID", node=nid, max=TIMEOUT[1]))
    ttl = data.get("cache_ttl")
    if ttl is not None and (isinstance(ttl, bool) or not isinstance(ttl, int) or not CACHE_TTL[0] <= ttl <= CACHE_TTL[1]):
        out.append(Issue("CACHE_TTL_INVALID", node=nid, min=CACHE_TTL[0], max=CACHE_TTL[1]))
    return out


def _retry_on(exc: Exception) -> bool:
    """LangGraph's default, except a Human pause is not a failed attempt."""
    if isinstance(exc, Interrupt): return False
    return bool(RetryPolicy().retry_on(exc))


def input_schema(data: Dict[str, Any], ann: Dict[str, Any]):
    """Typed dict of the fields this node may see, or None when it sees the whole state."""
    names = data.get("input_fields")
    if not isinstance(names, list) or not names:
        return None
    if any(not isinstance(name, str) or name not in ann for name in names):
        return None
    return TypedDict("NodeInput", {name: ann[name] for name in names}, total=False)  # type: ignore[misc]


def add_node_kwargs(data: Dict[str, Any]) -> Dict[str, Any]:
    """Arguments for `add_node` besides the function. Timeout is applied by `limit`, not here."""
    kw: Dict[str, Any] = {}
    retry = data.get("retry") if isinstance(data.get("retry"), dict) else {}
    attempts = retry.get("max_attempts")
    if _whole(attempts):
        wait = _num(retry.get("initial_interval"))
        kw["retry_policy"] = RetryPolicy(
            max_attempts=attempts, initial_interval=0.5 if wait is None else wait,
            backoff_factor=1.0, jitter=False, retry_on=_retry_on)
    ttl = data.get("cache_ttl")
    if _whole(ttl):
        kw["cache_policy"] = CachePolicy(ttl=ttl)
    return kw


def _whole(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def needs_cache(nodes: List[Dict[str, Any]]) -> bool:
    return any(_whole((n.get("data") or {}).get("cache_ttl")) for n in nodes)


def limit(fn: Callable[[dict], Any], seconds: float, name: str) -> Callable[[dict], Any]:
    """Return `fn(state)` or raise `NodeTimeoutError` once `seconds` have passed."""
    def run(state: dict) -> Any:
        box: Dict[str, Any] = {}
        ctx = contextvars.copy_context()

        def work() -> None:
            try: box["value"] = ctx.run(fn, state)
            except Exception as exc: box["error"] = exc

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        thread.join(seconds)
        if thread.is_alive():
            raise NodeTimeoutError(name, seconds, kind="run", run_timeout=seconds)
        if "error" in box: raise box["error"]
        return box.get("value")
    return run
