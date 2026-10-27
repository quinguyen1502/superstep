"""LLM provider registry (TASK-0030, DEC-0032): one small strategy class per provider.

A provider knows its defaults (base URL, whether a key is required, extra headers it accepts), how to list
models and how to build a LangChain chat model (streaming + `bind_tools` come with it). `call_llm`
(engine/llm.py) and the credential service only talk to `get(provider_id)`.

Adding a provider = subclass `OpenAICompatible` (or `Provider`) with a few attributes and append it to REGISTRY.
Errors are raised as `ProviderError(code, **params)`; codes live in core/errors.py (PROVIDER_*, MODEL_NOT_FOUND)."""
from __future__ import annotations
import json
from typing import Any, Callable, ClassVar, Dict, List, Optional, Tuple
import httpx
from ..core import config, smtp
from ..core.errors import CATALOG, AppError
from .usage import estimate_tokens, make_usage


class LLMError(Exception):
    pass


class ProviderError(LLMError):
    """LLM/provider failure with a catalog error code (the service turns it into AppError)."""
    def __init__(self, code: str, provider: str, reason: str = "", **params: Any):
        self.code, self.params = code, {"provider": provider, "reason": reason, "base_url": "", "model": "", **params}
        tmpl = CATALOG.get(code, (0, code))[1]
        try: text = tmpl.format(**self.params)
        except (KeyError, IndexError): text = tmpl
        super().__init__(f"{provider}: {text}")


def http_client() -> httpx.Client:
    """Factory for outbound provider HTTP calls (tests replace it or mock httpx with respx)."""
    return httpx.Client(timeout=60)


def _raise_for_status(provider: str, r: httpx.Response, model: str = "") -> None:
    if r.status_code < 400: return
    try: msg = r.json().get("error") or r.text
    except Exception: msg = r.text
    msg = (msg.get("message") if isinstance(msg, dict) else str(msg))[:200]
    if r.status_code in (401, 403): raise ProviderError("PROVIDER_AUTH_FAILED", provider, msg)
    if r.status_code == 404 and model: raise ProviderError("MODEL_NOT_FOUND", provider, msg, model=model)
    raise ProviderError("PROVIDER_BAD_RESPONSE", provider, f"HTTP {r.status_code}: {msg}")


def request(provider: str, method: str, url: str, headers: Dict[str, str], body: Any = None, model: str = "") -> Dict[str, Any]:
    try:
        with http_client() as c:
            r = c.request(method, url, headers=headers, json=body)
    except httpx.HTTPError as e:
        raise ProviderError("PROVIDER_UNREACHABLE", provider, type(e).__name__, base_url=str(url)) from None
    _raise_for_status(provider, r, model)
    try: return r.json()
    except ValueError: raise ProviderError("PROVIDER_BAD_RESPONSE", provider, "invalid JSON") from None


class Provider:
    id: ClassVar[str]
    label: ClassVar[str]
    default_base_url: ClassVar[str]
    default_model: ClassVar[str] = ""
    key_required: ClassVar[bool] = False
    header_fields: ClassVar[Tuple[str, ...]] = ()   # optional extra HTTP headers stored on the credential
    supports_tools: ClassVar[bool] = True
    local: ClassVar[bool] = False                    # runs on the user's machine (Docker: host.docker.internal)
    kind: ClassVar[str] = "chat"                     # "chat" (LLM nodes), "decision" (Decision nodes, TASK-0050), "email" (TASK-0051)
    settings_fields: ClassVar[Tuple[str, ...]] = ()  # non-secret settings stored on the credential (SMTP host, port, ...)

    def info(self) -> Dict[str, Any]:
        return {"id": self.id, "label": self.label, "default_base_url": self.default_base_url, "default_model": self.default_model,
                "key_required": self.key_required, "header_fields": list(self.header_fields), "settings_fields": list(self.settings_fields),
                "supports_tools": self.supports_tools, "streaming": self.kind == "chat", "local": self.local, "kind": self.kind,
                "supports_embeddings": self.supports_embeddings, "default_embedding_model": self.default_embedding_model}

    def clean_settings(self, raw: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Validated `settings` for a credential of this provider (raises CREDENTIAL_SETTINGS_INVALID)."""
        return {}

    @staticmethod
    def base(cred: Dict[str, Any], default: str) -> str:
        return (cred.get("base_url") or default).rstrip("/")

    def auth_headers(self, cred: Dict[str, Any]) -> Dict[str, str]:
        h = {k: v for k, v in (cred.get("headers") or {}).items() if k in self.header_fields and v}
        if cred.get("api_key"): h["Authorization"] = f"Bearer {cred['api_key']}"
        return h

    # --- model listing -----------------------------------------------------------------
    models_path: ClassVar[str] = "/models"

    def parse_models(self, data: Dict[str, Any]) -> List[str]:
        return sorted(m["id"] for m in data.get("data", []) if m.get("id"))

    def list_models(self, cred: Dict[str, Any]) -> List[str]:
        data = request(self.id, "GET", self.base(cred, self.default_base_url) + self.models_path, self.auth_headers(cred))
        try: return self.parse_models(data)
        except (TypeError, KeyError, AttributeError): raise ProviderError("PROVIDER_BAD_RESPONSE", self.id, "unexpected model list") from None

    # --- chat --------------------------------------------------------------------------
    def chat_model(self, cred: Dict[str, Any], model: str, **kw: Any):
        """LangChain chat model (supports .stream and .bind_tools)."""
        raise NotImplementedError

    def map_error(self, e: Exception, model: str) -> Optional[ProviderError]:
        return None

    stream_kwargs: ClassVar[Dict[str, Any]] = {}       # extra chat-model options when streaming (e.g. usage chunks)

    def invoke(self, prompt: str, model: str, cred: Dict[str, Any], on_token: Optional[Callable[[str], None]] = None) -> Tuple[str, Dict[str, Any]]:
        """Final text + usage. With `on_token` the LangChain model streams and every text delta is passed on as it arrives
        (the returned text is the same concatenation)."""
        model = model or self.default_model
        try:
            if on_token is None: msg = self.chat_model(cred, model).invoke(prompt)
            else:
                msg = None
                for chunk in self.chat_model(cred, model, **self.stream_kwargs).stream(prompt):
                    if (d := _text(chunk.content)): on_token(d)
                    msg = chunk if msg is None else msg + chunk
                if msg is None: raise ProviderError("PROVIDER_BAD_RESPONSE", self.id, "empty stream")
        except ProviderError: raise
        except Exception as e:  # SDK-specific exceptions → catalog codes
            mapped = self.map_error(e, model) or _map_http_error(e, self.id, model, self.base(cred, self.default_base_url))
            raise mapped from None
        out = _text(msg.content)
        u = getattr(msg, "usage_metadata", None) or {}
        usage = make_usage(self.id, model, u["input_tokens"], u["output_tokens"]) if u else \
            make_usage(self.id, model, estimate_tokens(prompt), estimate_tokens(out), estimated=True)
        return out.strip(), usage

    parallel_tool_calls_flag: ClassVar[bool] = False  # OpenAI-compatible servers accept parallel_tool_calls=false (DEC-0069)

    def invoke_tools(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]], model: str, cred: Dict[str, Any],
                     on_token: Optional[Callable[[str], None]] = None, parallel: Optional[bool] = None) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """One Agent node model call (TASK-0116): (text, tool calls [{id, name, args}], usage). `messages` are plain dicts
        {role: system|user|assistant|tool, content, tool_calls?, tool_call_id?}; `tools` [{name, description, parameters}].
        `parallel` False asks a server that supports it for one call at a time (DEC-0069)."""
        model = model or self.default_model
        try:
            m = self.chat_model(cred, model, **(self.stream_kwargs if on_token else {}))
            if tools:
                extra = {"parallel_tool_calls": False} if parallel is False and self.parallel_tool_calls_flag else {}
                m = m.bind_tools([{"type": "function", "function": t} for t in tools], **extra)
            if on_token is None: msg = m.invoke(_lc_messages(messages))
            else:
                msg = None
                for chunk in m.stream(_lc_messages(messages)):
                    if (d := _text(chunk.content)): on_token(d)
                    msg = chunk if msg is None else msg + chunk
                if msg is None: raise ProviderError("PROVIDER_BAD_RESPONSE", self.id, "empty stream")
        except ProviderError: raise
        except Exception as e:
            mapped = self.map_error(e, model) or _map_http_error(e, self.id, model, self.base(cred, self.default_base_url))
            raise mapped from None
        out = _text(msg.content).strip()
        calls = [{"id": c.get("id") or f"call_{i}", "name": c.get("name") or "", "args": c.get("args") or {}} for i, c in enumerate(getattr(msg, "tool_calls", None) or [])]
        u = getattr(msg, "usage_metadata", None) or {}
        usage = make_usage(self.id, model, u["input_tokens"], u["output_tokens"]) if u else \
            make_usage(self.id, model, estimate_tokens(json.dumps(messages, ensure_ascii=False)), estimate_tokens(out), estimated=True)
        return out, calls, usage

    # --- embeddings (knowledge bases) ----------------------------------------------------
    supports_embeddings: ClassVar[bool] = True
    default_embedding_model: ClassVar[str] = ""
    embeddings_path: ClassVar[str] = "/embeddings"
    embed_batch: ClassVar[int] = 96

    def embed_request(self, model: str, texts: List[str]) -> Dict[str, Any]:
        return {"model": model, "input": texts}

    def parse_embeddings(self, data: Dict[str, Any]) -> List[List[float]]:
        return [d["embedding"] for d in sorted(data["data"], key=lambda d: d.get("index", 0))]

    def embed(self, texts: List[str], model: str, cred: Dict[str, Any]) -> List[List[float]]:
        """One vector per text (OpenAI-style `/embeddings` by default). All vectors must share one dimension."""
        if not self.supports_embeddings: raise ProviderError("PROVIDER_EMBEDDINGS_UNSUPPORTED", self.id)
        model = model or self.default_embedding_model
        url, out = self.base(cred, self.default_base_url) + self.embeddings_path, []
        for i in range(0, len(texts), self.embed_batch):
            batch = texts[i:i + self.embed_batch]
            data = request(self.id, "POST", url, self.auth_headers(cred), self.embed_request(model, batch), model=model)
            try: vecs = self.parse_embeddings(data)
            except (TypeError, KeyError, AttributeError): raise ProviderError("PROVIDER_BAD_RESPONSE", self.id, "invalid embeddings response") from None
            if len(vecs) != len(batch): raise ProviderError("PROVIDER_BAD_RESPONSE", self.id, "embedding count mismatch")
            out += vecs
        if len({len(v) for v in out}) > 1: raise ProviderError("PROVIDER_BAD_RESPONSE", self.id, "embeddings of different dimensions")
        return out


def _lc_messages(messages: List[Dict[str, Any]]) -> list:
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
    out = []
    for m in messages:
        role, text = m.get("role"), m.get("content") or ""
        if role == "system": out.append(SystemMessage(text))
        elif role == "assistant": out.append(AIMessage(text, tool_calls=[{"id": c["id"], "name": c["name"], "args": c.get("args") or {}} for c in m.get("tool_calls") or []]))
        elif role == "tool": out.append(ToolMessage(text, tool_call_id=m.get("tool_call_id") or ""))
        else: out.append(HumanMessage(text))
    return out


def _text(content: Any) -> str:
    return content if isinstance(content, str) else "".join(b.get("text", "") for b in content if isinstance(b, dict))


def _map_http_error(e: Exception, provider: str, model: str, base_url: str = "") -> ProviderError:
    status = getattr(e, "status_code", None)
    name = type(e).__name__
    if isinstance(e, (httpx.HTTPError, ConnectionError)) or "Connection" in name or "Timeout" in name or name == "ConnectError":
        return ProviderError("PROVIDER_UNREACHABLE", provider, name, base_url=base_url)
    if status in (401, 403): return ProviderError("PROVIDER_AUTH_FAILED", provider, str(e)[:200])
    if status == 404: return ProviderError("MODEL_NOT_FOUND", provider, str(e)[:200], model=model)
    return ProviderError("PROVIDER_BAD_RESPONSE", provider, f"{name}: {str(e)[:200]}")


class OpenAICompatible(Provider):
    """Any server speaking the OpenAI Chat Completions API (vLLM, llama.cpp server, LocalAI, ...)."""
    id, label, default_base_url = "openai_compatible", "OpenAI-compatible (vLLM / llama.cpp / LocalAI)", "http://localhost:8000/v1"
    parallel_tool_calls_flag = True
    local = True
    stream_kwargs = {"stream_usage": True}  # final chunk carries token usage (ignored by servers that do not send it)

    def chat_model(self, cred, model, **kw):
        from langchain_openai import ChatOpenAI
        h = self.auth_headers(cred); h.pop("Authorization", None)
        return ChatOpenAI(model=model, base_url=self.base(cred, self.default_base_url), api_key=cred.get("api_key") or "not-needed",
                          default_headers=h or None, timeout=60, max_retries=0, **kw)


class LMStudio(OpenAICompatible):
    id, label, default_base_url = "lmstudio", "LM Studio", "http://localhost:1234/v1"


class OpenRouter(OpenAICompatible):
    id, label, default_base_url, default_model = "openrouter", "OpenRouter", "https://openrouter.ai/api/v1", "openrouter/auto"
    key_required, local = True, False
    header_fields = ("HTTP-Referer", "X-Title")
    default_embedding_model = "openai/text-embedding-3-small"


class Ollama(Provider):
    id, label, default_base_url, default_model = "ollama", "Ollama", "http://localhost:11434", "llama3.2"
    local, models_path = True, "/api/tags"
    default_embedding_model, embeddings_path = "nomic-embed-text", "/api/embed"

    def parse_embeddings(self, data): return data["embeddings"]

    def parse_models(self, data):
        return sorted(m.get("model") or m["name"] for m in data.get("models", []))

    def chat_model(self, cred, model, **kw):
        from langchain_ollama import ChatOllama
        h = self.auth_headers(cred)
        return ChatOllama(model=model, base_url=self.base(cred, self.default_base_url), client_kwargs={"headers": h, "timeout": 60}, **kw)

    def map_error(self, e, model):
        if type(e).__name__ == "ResponseError" and getattr(e, "status_code", None) == 404:
            return ProviderError("MODEL_NOT_FOUND", self.id, str(e)[:200], model=model)
        return None


class PlainHTTP(Provider):
    """Providers called over plain HTTP (no token streaming): `_complete` returns (text, usage); a stream gets one delta."""
    def _complete(self, prompt: str, model: str, cred: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]: raise NotImplementedError

    def invoke(self, prompt, model, cred, on_token=None):
        out, usage = self._complete(prompt, model or self.default_model, cred)
        if on_token and out: on_token(out)
        return out, usage


class OpenAI(PlainHTTP):
    """Hosted OpenAI (kept on plain HTTP like before TASK-0030; `ChatOpenAI` handles the same base URL for tools)."""
    id, label, default_base_url, default_model, key_required = "openai", "OpenAI / OpenAI-compatible", "https://api.openai.com/v1", "gpt-4o-mini", True
    stream_kwargs = {"stream_usage": True}  # Agent node calls go through ChatOpenAI (invoke_tools)
    parallel_tool_calls_flag = True

    def chat_model(self, cred, model, **kw): return OpenAICompatible.chat_model(self, cred, model, **kw)

    default_embedding_model = "text-embedding-3-small"

    def _complete(self, prompt, model, cred):
        data = request(self.id, "POST", self.base(cred, self.default_base_url) + "/chat/completions", self.auth_headers(cred),
                       {"model": model, "messages": [{"role": "user", "content": prompt}]}, model=model)
        try: out = data["choices"][0]["message"]["content"].strip()
        except Exception: raise ProviderError("PROVIDER_BAD_RESPONSE", self.id, "invalid response") from None
        u = data.get("usage") or {}
        return out, (make_usage(self.id, data.get("model") or model, u.get("prompt_tokens", 0), u.get("completion_tokens", 0)) if u
                     else make_usage(self.id, model, estimate_tokens(prompt), estimate_tokens(out), estimated=True))


class Anthropic(PlainHTTP):
    id, label, default_base_url, default_model, key_required = "anthropic", "Anthropic", "https://api.anthropic.com", "claude-3-5-haiku-latest", True
    models_path, supports_embeddings = "/v1/models", False

    def auth_headers(self, cred): return {"x-api-key": cred.get("api_key") or "", "anthropic-version": "2023-06-01"}

    def invoke_tools(self, messages, tools, model, cred, on_token=None, parallel=None):
        """The Messages API with `tools` over plain HTTP (no LangChain package for Anthropic): tool results go back as
        `tool_result` blocks in one user turn."""
        model = model or self.default_model
        system = "\n\n".join(m.get("content") or "" for m in messages if m.get("role") == "system")
        turns: List[Dict[str, Any]] = []
        for m in messages:
            role, text = m.get("role"), m.get("content") or ""
            if role == "system": continue
            if role == "tool":
                block = {"type": "tool_result", "tool_use_id": m.get("tool_call_id") or "", "content": text}
                if turns and turns[-1]["role"] == "user" and isinstance(turns[-1]["content"], list): turns[-1]["content"].append(block)
                else: turns.append({"role": "user", "content": [block]})
            elif role == "assistant":
                blocks = ([{"type": "text", "text": text}] if text else []) + [
                    {"type": "tool_use", "id": c["id"], "name": c["name"], "input": c.get("args") or {}} for c in m.get("tool_calls") or []]
                turns.append({"role": "assistant", "content": blocks or text})
            else: turns.append({"role": "user", "content": text})
        body: Dict[str, Any] = {"model": model, "max_tokens": 1024, "messages": turns}
        if system: body["system"] = system
        if tools:
            body["tools"] = [{"name": t["name"], "description": t.get("description") or "", "input_schema": t.get("parameters") or {"type": "object"}} for t in tools]
            if parallel is False: body["tool_choice"] = {"type": "auto", "disable_parallel_tool_use": True}
        data = request(self.id, "POST", self.base(cred, self.default_base_url) + "/v1/messages", self.auth_headers(cred), body, model=model)
        try:
            blocks = data["content"]
            out = "".join(b.get("text", "") for b in blocks if b.get("type") == "text").strip()
            calls = [{"id": b["id"], "name": b["name"], "args": b.get("input") or {}} for b in blocks if b.get("type") == "tool_use"]
        except Exception: raise ProviderError("PROVIDER_BAD_RESPONSE", self.id, "invalid response") from None
        if on_token and out: on_token(out)
        u = data.get("usage") or {}
        return out, calls, make_usage(self.id, data.get("model") or model, u.get("input_tokens", 0), u.get("output_tokens", 0))

    def _complete(self, prompt, model, cred):
        data = request(self.id, "POST", self.base(cred, self.default_base_url) + "/v1/messages", self.auth_headers(cred),
                       {"model": model, "max_tokens": 1024, "messages": [{"role": "user", "content": prompt}]}, model=model)
        try: out = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text").strip()
        except Exception: raise ProviderError("PROVIDER_BAD_RESPONSE", self.id, "invalid response") from None
        u = data.get("usage") or {}
        return out, make_usage(self.id, data.get("model") or model, u.get("input_tokens", 0), u.get("output_tokens", 0))


class TypeSafe(Provider):
    """TypeSafe System One (TASK-0050, DEC-0039). Jev returns typed decisions (choice, score, noul) with probabilities,
    not text, so it serves Decision nodes only. The key check sends one tiny question (there is no model list endpoint)."""
    id, label, default_base_url, default_model, key_required = "typesafe", "TypeSafe (Jev)", "https://api.typesafe.ai", "jev-latest", True
    kind, supports_tools, supports_embeddings = "decision", False, False

    def chat_model(self, cred, model, **kw):
        raise ProviderError("PROVIDER_BAD_RESPONSE", self.id, "TypeSafe answers Decision nodes, not prompts")

    def decide(self, body: Dict[str, Any], cred: Dict[str, Any]) -> Dict[str, Any]:
        data = request(self.id, "POST", self.base(cred, self.default_base_url) + "/v1/systemone", self.auth_headers(cred), body, model=body.get("model", ""))
        if not isinstance(data.get("answers"), dict): raise ProviderError("PROVIDER_BAD_RESPONSE", self.id, "no answers in the response")
        return data

    def list_models(self, cred):
        data = self.decide({"state": "ping", "model": self.default_model, "questions": {"ok": {"type": "noul", "instructions": "This is a connection test."}}}, cred)
        return sorted({self.default_model, str(data.get("model") or self.default_model)})


class Smtp(Provider):
    """An SMTP server for Send email nodes (TASK-0051, DEC-0040). The password is the credential's secret; host, port,
    security, username and sender are its settings. The check connects, upgrades to TLS and signs in, then quits."""
    id, label, default_base_url = "smtp", "SMTP (e-mail)", ""
    kind, supports_tools, supports_embeddings = "email", False, False
    settings_fields = ("host", "port", "security", "username", "from_email", "from_name")

    def chat_model(self, cred, model, **kw):
        raise ProviderError("PROVIDER_BAD_RESPONSE", self.id, "an SMTP credential sends e-mail, it does not answer prompts")

    def clean_settings(self, raw):
        r = raw or {}
        def bad(field: str): return AppError("CREDENTIAL_SETTINGS_INVALID", field=field)
        host = str(r.get("host") or "").strip().lower()
        if not host or len(host) > 253 or any(ch.isspace() or ch in "/@:" for ch in host): raise bad("host")
        try: port = int(r.get("port") or 587)
        except (TypeError, ValueError): raise bad("port") from None
        if not 1 <= port <= 65535: raise bad("port")
        security = r.get("security") or "starttls"
        if security not in smtp.SECURITY: raise bad("security")
        sender = str(r.get("from_email") or "").strip()
        if not smtp.ADDRESS_RE.match(sender) or len(sender) > 254: raise bad("from_email")
        user, name = str(r.get("username") or "").strip(), " ".join(str(r.get("from_name") or "").split())
        if len(user) > 256: raise bad("username")
        if len(name) > 100: raise bad("from_name")
        return {"host": host, "port": port, "security": security, "username": user, "from_email": sender, "from_name": name}

    def smtp_settings(self, cred: Dict[str, Any]) -> Dict[str, Any]:
        """core/smtp.py settings for this credential; private hosts only with STUDIO_SMTP_ALLOW_PRIVATE=1."""
        s = cred.get("settings") or {}
        return {"host": s.get("host"), "port": s.get("port") or 587, "security": s.get("security") or "starttls",
                "username": s.get("username") or None, "password": cred.get("api_key") or None, "sender": s.get("from_email"),
                "from_name": s.get("from_name") or "", "allow_private": config.email_node_allow_private()}

    def list_models(self, cred):
        smtp.check(self.smtp_settings(cred)); return []


REGISTRY: Dict[str, Provider] = {p.id: p for p in (OpenAI(), Anthropic(), Ollama(), LMStudio(), OpenAICompatible(), OpenRouter(), TypeSafe(), Smtp())}


def get(provider_id: str) -> Optional[Provider]:
    return REGISTRY.get(provider_id)
