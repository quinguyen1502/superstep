"""LLM calls for the LLM node: dispatches to the provider registry (engine/providers.py), deterministic mock otherwise.

Credentials arrive already decrypted from the run's resolver (services.credential_service);
without one, OPENAI_API_KEY from the environment is used, then the mock."""
from __future__ import annotations
import os, re, time
from contextlib import contextmanager
from typing import Any, Callable, Dict, Iterator, List, Optional, Tuple
from . import attachments, providers
from .providers import LLMError, ProviderError  # noqa: F401 (re-exported)
from .locale import LOCALES, by_locale, text as locale_text
from .usage import estimate_tokens, make_usage


MOCK_ANSWER = by_locale("mock.answer")  # the echo's prefix per language (app/locales)
# Words the mock looks for in a classification prompt, in every language (app/locales).
CLASSIFY = {part: [w for lang in LOCALES for w in locale_text(lang, f"mock.classify.{part}")] for part in ("markers", "order", "refund")}


def mock_llm(prompt: str, model: str, locale: str = "en") -> str:
    """Deterministic offline mock. Recognises classification prompts; the echo is in `locale` (en, vi)."""
    p = prompt.lower()
    if any(k in p for k in CLASSIFY["markers"]):
        msg = p.split("message:")[-1] if "message:" in p else p
        if any(k in msg for k in CLASSIFY["order"]):
            return "order_status"
        if any(k in msg for k in CLASSIFY["refund"]):
            return "refund"
        return "general"
    tail = prompt.strip().splitlines()[-1] if prompt.strip() else ""
    return f"[mock:{model}] {MOCK_ANSWER.get(locale, MOCK_ANSWER['en'])}: {tail[:200]}"


# ---- per-call timing: one record per provider call (mock calls are not measured) ----
CallObserver = Callable[[Dict[str, Any]], None]
_observers: List[CallObserver] = []


def observe(fn: CallObserver) -> None:
    """Register a callback for every measured call: {kind, provider, model, status, duration_ms, ttft_ms}. The service
    layer turns these into metrics; the engine itself knows nothing about them."""
    if fn not in _observers: _observers.append(fn)


def unobserve(fn: CallObserver) -> None:
    if fn in _observers: _observers.remove(fn)


def emit_call(record: Dict[str, Any]) -> None:
    for fn in list(_observers):
        try: fn(record)
        except Exception: pass  # metrics never fail a call


def call_status(e: BaseException) -> str:
    """`ok`, a provider error code (PROVIDER_*, MODEL_NOT_FOUND) or `error`: a bounded value for a metric label."""
    code = getattr(e, "code", None)
    return code if isinstance(code, str) and (code.startswith("PROVIDER_") or code == "MODEL_NOT_FOUND") else "error"


class Measure:
    """Times one provider call; `on_token` wraps the caller's token callback to note the first non-empty delta."""
    def __init__(self, provider: str, model: str, on_token: Optional[Callable[[str], None]], kind: str = "llm"):
        self.provider, self.model, self.kind, self._user = provider, model, kind, on_token
        self.t0 = time.perf_counter(); self.first: Optional[float] = None; self.done = False
        self.on_token = self._token if on_token else None

    def _token(self, delta: str) -> None:
        if self.first is None and delta: self.first = time.perf_counter()
        self._user(delta)

    def finish(self, usage: Optional[Dict[str, Any]] = None, status: str = "ok") -> Optional[Dict[str, Any]]:
        """Report the call once; returns the usage record with `duration_ms` (and `ttft_ms` when streamed) added."""
        if self.done: return usage
        self.done = True
        ms = round((time.perf_counter() - self.t0) * 1000, 2)
        ttft = round((self.first - self.t0) * 1000, 2) if self.first is not None else None
        emit_call({"kind": self.kind, "provider": self.provider, "model": self.model, "status": status, "duration_ms": ms, "ttft_ms": ttft})
        if usage is None: return None
        return {**usage, "duration_ms": ms, **({"ttft_ms": ttft} if ttft is not None else {})}


@contextmanager
def measure(provider: str, model: str, on_token: Optional[Callable[[str], None]] = None, kind: str = "llm") -> Iterator[Measure]:
    m = Measure(provider, model, on_token, kind)
    try: yield m
    except BaseException as e:
        m.finish(status=call_status(e)); raise
    m.finish()


class TokenBuffer:
    """Coalesces streamed text deltas so the run stream carries a few events per second, not one per token."""
    def __init__(self, emit: Callable[[str], None], interval: float = 0.05):
        self.emit, self.interval, self.buf, self.last = emit, interval, [], time.monotonic()

    def __call__(self, delta: str) -> None:
        self.buf.append(delta)
        if time.monotonic() - self.last >= self.interval: self.flush()

    def flush(self) -> None:
        if self.buf: self.emit("".join(self.buf)); self.buf.clear()
        self.last = time.monotonic()


def call_llm(prompt: str, model: str, cred: Optional[Dict[str, Any]] = None, on_usage=None,
             on_token: Optional[Callable[[str], None]] = None, mock: bool = False, locale: str = "en",
             files: Optional[List[Dict[str, Any]]] = None, load: Optional[attachments.Load] = None) -> str:
    """cred: decrypted credential {provider, base_url, api_key, headers}. Without cred falls back to env OPENAI_API_KEY, then mock.
    on_usage(usage): optional callback with the token usage record (engine/usage.make_usage).
    on_token(delta): optional callback with text deltas as the model streams them; the return value is unchanged.
    mock: always the offline mock, whatever the credential (test runs with the mock option, ).
    locale: the language of the mock's answers (engine/locale).
    files: chat attachment records sent with the prompt; `load` reads an image's bytes by id."""
    report = on_usage or (lambda u: None)
    if cred is None or mock:
        key = None if mock else os.environ.get("OPENAI_API_KEY")
        if not key:
            out = mock_llm(prompt, model, locale)
            if files: out = f"{out}\n{attachments.summary(files, locale)}"  # the mock names what it got
            if on_token:  # the mock streams word by word so the live trace works offline too
                for w in re.findall(r"\S+\s*", out): on_token(w)
            report(make_usage("mock", model, estimate_tokens(prompt), estimate_tokens(out), estimated=True))
            return out
        cred = {"provider": "openai", "api_key": key, "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")}
    p = providers.get(cred["provider"])
    if p is None: raise LLMError(f"Unsupported provider: {cred['provider']}")
    images = None
    if files: prompt, images = attachments.build(prompt, files, providers.vision(cred["provider"], model), load)
    with measure(cred["provider"], model, on_token) as m:
        out, usage = p.invoke(prompt, model, cred, m.on_token, images=images) if images else p.invoke(prompt, model, cred, m.on_token)
        usage = m.finish(usage)
    report(usage)
    return out


def _task(messages: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """The last user message and the tool results after it."""
    last = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=-1)
    return (messages[last].get("content") or "") if last >= 0 else "", [m for m in messages[last + 1:] if m.get("role") == "tool"]


def _mock_call(tool: Dict[str, Any], task: str, n: int) -> Dict[str, Any]:
    """One mock tool call: string arguments are the task text, or the first allowed value of an enum.
    Required objects with declared properties fill their text properties the same way. Other JSON types are empty."""
    params = tool.get("parameters") or {}
    props, required = params.get("properties") or {}, set(params.get("required") or [])
    empty = {"number": 0, "integer": 0, "boolean": False, "array": [], "object": {}}

    def text(v: Dict[str, Any]) -> bool:
        kind = v.get("type", "string")
        return kind == "string" or isinstance(kind, list) and "string" in kind

    def value(v: Dict[str, Any]) -> Any:
        if v.get("enum"): return v["enum"][0]
        if text(v): return task
        if v.get("type") == "object" and v.get("properties"):
            return {k: value(p or {}) for k, p in v["properties"].items() if text(p or {})}
        return empty.get(v.get("type"))

    args = {k: value(v or {}) for k, v in props.items() if k in required or (v or {}).get("type", "string") == "string"}
    if args.get("operation") in ("insert_row", "upsert_row") and isinstance(props.get("values"), dict):
        args["values"] = value(props["values"])  # a Dataset write tool: the mock writes the task text
    return {"id": f"mock_call_{n}", "name": tool["name"], "args": args}


def _named_tools(tools: List[Dict[str, Any]], task: str) -> List[Dict[str, Any]]:
    """Tools whose name the task contains as a whole token, in tool-list order (underscores may be spaces)."""
    text = task.lower()
    found = []
    for t in tools:
        name = str(t.get("name") or "")
        if not name: continue
        forms = {name.lower(), name.lower().replace("_", " ")}
        if any(re.search(rf"(?<!\w){re.escape(form)}(?!\w)", text) for form in forms): found.append(t)
    return found


def mock_agent(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]], model: str, locale: str = "en") -> Tuple[str, List[Dict[str, Any]]]:
    """Deterministic offline agent. With no tool result yet it calls the tool whose name and
    description share the most words with the task (the first tool on a tie). When the task names two or more tools,
    it calls each of them. String parameters are the task text. Then it answers with the last tool result."""
    task, results = _task(messages)
    if tools and not results:
        named = _named_tools(tools, task)
        if len(named) >= 2: return "", [_mock_call(t, task, i) for i, t in enumerate(named, 1)]
        words = set(re.findall(r"\w+", task.lower()))
        score = lambda t: len(words & set(re.findall(r"\w+", f"{t['name'].replace('_', ' ')} {t.get('description') or ''}".lower())))
        return "", [_mock_call(max(tools, key=score), task, 1)]  # max keeps the first of equal scores
    said = (results[-1].get("content") or "") if results else (task.strip().splitlines() or [""])[-1]
    return f"[mock:{model}] {MOCK_ANSWER.get(locale, MOCK_ANSWER['en'])}: {said[:200]}", []


def with_files(messages: List[Dict[str, Any]], vision: bool, load: Optional[attachments.Load]) -> List[Dict[str, Any]]:
    """Messages whose `files` (chat attachments, ) become text blocks, notes and `images` for the provider."""
    out = []
    for m in messages:
        if not m.get("files"): out.append({k: v for k, v in m.items() if k != "files"}); continue
        text, images = attachments.build(m.get("content") or "", m["files"], vision, load)
        out.append({**{k: v for k, v in m.items() if k != "files"}, "content": text, **({"images": images} if images else {})})
    return out


def call_agent(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]], model: str, cred: Optional[Dict[str, Any]] = None,
               on_usage=None, on_token: Optional[Callable[[str], None]] = None, mock: bool = False,
               locale: str = "en", parallel: Optional[bool] = None, load: Optional[attachments.Load] = None) -> Tuple[str, List[Dict[str, Any]]]:
    """One Agent node model call: (text, tool calls [{id, name, args}]). `tools` [{name, description, parameters}];
    None or [] asks for an answer without tools. Credentials, the env key and the mock as for `call_llm`.
    `parallel` False asks the provider for one call at a time when it supports that flag."""
    report = on_usage or (lambda u: None)
    if cred is None or mock:
        key = None if mock else os.environ.get("OPENAI_API_KEY")
        if not key:
            out, calls = mock_agent(messages, tools, model, locale)
            files = [f for m in messages if m.get("role") == "user" for f in (m.get("files") or [])]
            if out and files: out = f"{out}\n{attachments.summary(files, locale)}"  # the mock names what it got
            if on_token and out:
                for w in re.findall(r"\S+\s*", out): on_token(w)
            report(make_usage("mock", model, estimate_tokens(" ".join(str(m.get("content") or "") for m in messages)), estimate_tokens(out), estimated=True))
            return out, calls
        cred = {"provider": "openai", "api_key": key, "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")}
    p = providers.get(cred["provider"])
    if p is None: raise LLMError(f"Unsupported provider: {cred['provider']}")
    if not p.supports_tools: raise ProviderError("AGENT_TOOLS_UNSUPPORTED", p.label)
    if any(m.get("files") for m in messages): messages = with_files(messages, providers.vision(cred["provider"], model), load)
    with measure(cred["provider"], model, on_token) as m:
        out, calls, usage = p.invoke_tools(messages, tools or [], model, cred, m.on_token, parallel=parallel)
        usage = m.finish(usage)
    report(usage)
    return out, calls


def chat_model(cred: Dict[str, Any], model: str, **kw: Any):
    """LangChain chat model for a decrypted credential (streaming, `bind_tools`)."""
    p = providers.get(cred["provider"])
    if p is None: raise LLMError(f"Unsupported provider: {cred['provider']}")
    return p.chat_model(cred, model or p.default_model, **kw)
