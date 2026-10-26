"""LLM calls for the LLM node: dispatches to the provider registry (engine/providers.py), deterministic mock otherwise.

Credentials arrive already decrypted from the run's resolver (services.credential_service);
without one, OPENAI_API_KEY from the environment is used, then the mock."""
from __future__ import annotations
import os, re, time
from typing import Any, Callable, Dict, List, Optional, Tuple
from . import providers
from .providers import LLMError, ProviderError  # noqa: F401 (re-exported)
from .usage import estimate_tokens, make_usage


MOCK_ANSWER = {"en": "Answer", "vi": "Trả lời"}  # the echo's prefix per language (engine/locale)


def mock_llm(prompt: str, model: str, locale: str = "en") -> str:
    """Deterministic offline mock. Recognises classification prompts; the echo is in `locale` (en, vi)."""
    p = prompt.lower()
    if "classify" in p or "phân loại" in p:
        msg = p.split("message:")[-1] if "message:" in p else p
        if any(k in msg for k in ["order", "đơn", "giao hàng", "ship", "a100", "b200", "c300"]):
            return "order_status"
        if any(k in msg for k in ["refund", "hoàn tiền", "return"]):
            return "refund"
        return "general"
    tail = prompt.strip().splitlines()[-1] if prompt.strip() else ""
    return f"[mock:{model}] {MOCK_ANSWER.get(locale, MOCK_ANSWER['en'])}: {tail[:200]}"


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
             on_token: Optional[Callable[[str], None]] = None, mock: bool = False, locale: str = "en") -> str:
    """cred: decrypted credential {provider, base_url, api_key, headers}. Without cred falls back to env OPENAI_API_KEY, then mock.
    on_usage(usage): optional callback with the token usage record (engine/usage.make_usage).
    on_token(delta): optional callback with text deltas as the model streams them (TASK-0030); the return value is unchanged.
    mock: always the offline mock, whatever the credential (test runs with the mock option, TASK-0067).
    locale: the language of the mock's answers (engine/locale)."""
    report = on_usage or (lambda u: None)
    if cred is None or mock:
        key = None if mock else os.environ.get("OPENAI_API_KEY")
        if not key:
            out = mock_llm(prompt, model, locale)
            if on_token:  # the mock streams word by word so the live trace works offline too
                for w in re.findall(r"\S+\s*", out): on_token(w)
            report(make_usage("mock", model, estimate_tokens(prompt), estimate_tokens(out), estimated=True))
            return out
        cred = {"provider": "openai", "api_key": key, "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")}
    p = providers.get(cred["provider"])
    if p is None: raise LLMError(f"Unsupported provider: {cred['provider']}")
    out, usage = p.invoke(prompt, model, cred, on_token)
    report(usage)
    return out


def _task(messages: List[Dict[str, Any]]) -> Tuple[str, List[Dict[str, Any]]]:
    """The last user message and the tool results after it."""
    last = max((i for i, m in enumerate(messages) if m.get("role") == "user"), default=-1)
    return (messages[last].get("content") or "") if last >= 0 else "", [m for m in messages[last + 1:] if m.get("role") == "tool"]


def mock_agent(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]], model: str, locale: str = "en") -> Tuple[str, List[Dict[str, Any]]]:
    """Deterministic offline agent (TASK-0116, DEC-0063): with no tool result yet it calls the tool whose name and description
    share the most words with the task (the first tool on a tie), string parameters filled with the task text; then it
    answers with the last tool result."""
    task, results = _task(messages)
    if tools and not results:
        words = set(re.findall(r"\w+", task.lower()))
        score = lambda t: len(words & set(re.findall(r"\w+", f"{t['name'].replace('_', ' ')} {t.get('description') or ''}".lower())))
        best = max(tools, key=score)  # max keeps the first of equal scores
        params = best.get("parameters") or {}
        props, required = params.get("properties") or {}, set(params.get("required") or [])
        empty = {"number": 0, "integer": 0, "boolean": False, "array": [], "object": {}}
        args = {k: task if (v or {}).get("type", "string") == "string" else empty.get((v or {}).get("type"))
                for k, v in props.items() if k in required or (v or {}).get("type", "string") == "string"}
        return "", [{"id": "mock_call_1", "name": best["name"], "args": args}]
    said = (results[-1].get("content") or "") if results else (task.strip().splitlines() or [""])[-1]
    return f"[mock:{model}] {MOCK_ANSWER.get(locale, MOCK_ANSWER['en'])}: {said[:200]}", []


def call_agent(messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]], model: str, cred: Optional[Dict[str, Any]] = None,
               on_usage=None, on_token: Optional[Callable[[str], None]] = None, mock: bool = False,
               locale: str = "en") -> Tuple[str, List[Dict[str, Any]]]:
    """One Agent node model call (TASK-0116): (text, tool calls [{id, name, args}]). `tools` [{name, description, parameters}];
    None or [] asks for an answer without tools. Credentials, the env key and the mock as for `call_llm`."""
    report = on_usage or (lambda u: None)
    if cred is None or mock:
        key = None if mock else os.environ.get("OPENAI_API_KEY")
        if not key:
            out, calls = mock_agent(messages, tools, model, locale)
            if on_token and out:
                for w in re.findall(r"\S+\s*", out): on_token(w)
            report(make_usage("mock", model, estimate_tokens(" ".join(str(m.get("content") or "") for m in messages)), estimate_tokens(out), estimated=True))
            return out, calls
        cred = {"provider": "openai", "api_key": key, "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")}
    p = providers.get(cred["provider"])
    if p is None: raise LLMError(f"Unsupported provider: {cred['provider']}")
    if not p.supports_tools: raise ProviderError("AGENT_TOOLS_UNSUPPORTED", p.label)
    out, calls, usage = p.invoke_tools(messages, tools or [], model, cred, on_token)
    report(usage)
    return out, calls


def chat_model(cred: Dict[str, Any], model: str, **kw: Any):
    """LangChain chat model for a decrypted credential (streaming, `bind_tools`)."""
    p = providers.get(cred["provider"])
    if p is None: raise LLMError(f"Unsupported provider: {cred['provider']}")
    return p.chat_model(cred, model or p.default_model, **kw)
