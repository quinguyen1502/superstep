"""Counts of integration activity (channels, MCP, browser, sandbox, product limits) for metrics.

Code that talks to an integration calls `emit(event, **fields)` with bounded fields only (a platform kind, a
transport, a runtime, a status or an error code), never a server name, URL, user id or run id. The service layer
registers one observer that turns events into metrics; with none registered `emit` does nothing."""
from __future__ import annotations
import time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List

Observer = Callable[[str, Dict[str, Any]], None]
_observers: List[Observer] = []


def observe(fn: Observer) -> None:
    if fn not in _observers: _observers.append(fn)


def unobserve(fn: Observer) -> None:
    if fn in _observers: _observers.remove(fn)


def emit(event: str, **fields: Any) -> None:
    for fn in list(_observers):
        try: fn(event, fields)
        except Exception: pass  # metrics never fail the call they describe


def error_code(e: BaseException, default: str) -> str:
    """The catalog code of an error (AppError, ProviderError, McpError), else `default`: a bounded label value."""
    code = getattr(e, "code", None)
    return code if isinstance(code, str) and code.isupper() and len(code) <= 64 else default


@contextmanager
def timed(event: str, error: str, **fields: Any) -> Iterator[Dict[str, Any]]:
    """Emit one `event` with `status` (ok or error), `code` and `duration_ms` around a block. The block may set
    `status` in the yielded dict."""
    out: Dict[str, Any] = {"status": "ok", "code": ""}; t0 = time.perf_counter()
    try: yield out
    except BaseException as e:
        out.update(status="error", code=error_code(e, error)); raise
    finally:
        emit(event, **fields, **out, duration_ms=round((time.perf_counter() - t0) * 1000, 2))
