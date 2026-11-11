"""Logger helper so modules share the `studio.*` namespace, token redaction for uvicorn's logs, and log correlation.

`STUDIO_LOG_FORMAT=json` turns API, worker and uvicorn logs into one JSON object per line carrying the request id
(`X-Request-ID`), the run and workflow ids of the run being executed and the current trace and span ids. The default
`text` format leaves output as it was. Records never gain prompts, inputs, outputs or secrets; `token=` values stay
redacted in both formats.
"""
from __future__ import annotations
import contextvars, json, logging, re, sys, time, uuid
from contextlib import contextmanager
from typing import Iterator, Optional

TOKEN_RE = re.compile(r"(token=)[^&\s\"']+")
SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")  # an incoming X-Request-ID is kept only when it looks like this
FORMATS = ("text", "json")
TEXT_FORMAT = "%(levelname)s %(name)s: %(message)s"
UVICORN = ("uvicorn", "uvicorn.error", "uvicorn.access")
ID_FIELDS = ("request_id", "run_id", "workflow_id", "trace_id", "span_id")

_request_id: contextvars.ContextVar[str] = contextvars.ContextVar("studio_request_id", default="")
_run: contextvars.ContextVar[Optional[dict]] = contextvars.ContextVar("studio_run", default=None)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"studio.{name}")


def redact(text: str) -> str:
    return TOKEN_RE.sub(r"\1***", text)


class RedactTokens(logging.Filter):
    """Hide `token=` query values (the WebSocket JWT) in access and connection log lines."""
    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str): record.msg = redact(record.msg)
        if isinstance(record.args, tuple): record.args = tuple(redact(a) if isinstance(a, str) else a for a in record.args)
        return True


def redact_tokens(*names: str) -> None:
    for n in names:
        lg = logging.getLogger(n)
        if not any(isinstance(f, RedactTokens) for f in lg.filters): lg.addFilter(RedactTokens())


# ---- correlation context ----
def safe_request_id(value: Optional[str]) -> str:
    """The incoming id when it is a short safe token, else a new one (an unsafe value is never kept or logged)."""
    v = (value or "").strip()
    return v if SAFE_REQUEST_ID.match(v) else uuid.uuid4().hex


@contextmanager
def request_context(request_id: str) -> Iterator[str]:
    token = _request_id.set(request_id)
    try: yield request_id
    finally: _request_id.reset(token)


@contextmanager
def run_context(run_id: str, workflow_id: Optional[str] = None) -> Iterator[dict]:
    """Ids of the run being executed; threads started through `contextvars.copy_context()` see them too."""
    token = _run.set({"run_id": run_id or "", "workflow_id": workflow_id or "", "trace_id": ""})
    try: yield _run.get()
    finally: _run.reset(token)


def bind_trace(trace_id: Optional[str]) -> None:
    """The trace of the run in context (known once its root span is open)."""
    r = _run.get()
    if r is not None and trace_id: r["trace_id"] = trace_id


def _otel_ids() -> tuple[str, str]:
    if "opentelemetry.trace" not in sys.modules: return "", ""  # tracing never loaded: nothing to look up
    from opentelemetry import trace
    c = trace.get_current_span().get_span_context()
    return (format(c.trace_id, "032x"), format(c.span_id, "016x")) if c.is_valid else ("", "")


def current_ids() -> dict:
    """request_id, run_id, workflow_id, trace_id and span_id known in this context (empty strings otherwise)."""
    r = _run.get() or {}; trace_id, span_id = _otel_ids()
    return {"request_id": _request_id.get(), "run_id": r.get("run_id") or "", "workflow_id": r.get("workflow_id") or "",
            "trace_id": trace_id or r.get("trace_id") or "", "span_id": span_id}


class ContextFilter(logging.Filter):
    """Adds the correlation ids to every record as attributes (the text format does not print them)."""
    def filter(self, record: logging.LogRecord) -> bool:
        for k, v in current_ids().items(): setattr(record, k, v)
        return True


class JsonFormatter(logging.Formatter):
    """One JSON object per line: ts, level, logger, message, the ids that are known, and the exception if any."""
    def format(self, record: logging.LogRecord) -> str:
        out = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)) + f".{int(record.msecs):03d}Z",
               "level": record.levelname, "logger": record.name, "message": redact(record.getMessage())}
        ids = {k: getattr(record, k, "") for k in ID_FIELDS} if hasattr(record, "request_id") else current_ids()
        out.update({k: v for k, v in ids.items() if v})
        if record.exc_info: out["exception"] = redact(self.formatException(record.exc_info))
        return json.dumps(out, ensure_ascii=False, default=str)


def json_handler(stream=None) -> logging.Handler:
    h = logging.StreamHandler(stream or sys.stderr)
    h.setFormatter(JsonFormatter()); h.addFilter(ContextFilter()); h.addFilter(RedactTokens())
    return h


def configure(fmt: str = "text", level: str = "") -> None:
    """Called once by the API and the worker. `json`: one handler on the root logger; uvicorn's loggers propagate to it.
    `text` (default): output unchanged; a level, when given, prints `studio.*` records from that level on."""
    lvl = logging.getLevelName(level.upper()) if level else None
    if not isinstance(lvl, int): lvl = None
    if fmt == "json":
        root = logging.getLogger()
        root.handlers = [json_handler()]; root.setLevel(lvl or logging.INFO)
        for n in UVICORN:
            lg = logging.getLogger(n); lg.handlers = []; lg.propagate = True
        if lvl is not None: logging.getLogger("studio").setLevel(lvl)
        return
    if lvl is not None:
        lg = logging.getLogger("studio"); lg.setLevel(lvl)
        if not lg.handlers:
            h = logging.StreamHandler(); h.setFormatter(logging.Formatter(TEXT_FORMAT)); lg.addHandler(h)
