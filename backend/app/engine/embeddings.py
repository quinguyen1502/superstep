"""Text embeddings for knowledge bases: any embedding-capable provider of the registry (:
OpenAI, Ollama `/api/embed`, LM Studio / OpenAI-compatible / OpenRouter `/embeddings`), deterministic mock offline.

Selection mirrors engine/llm: a decrypted credential, else OPENAI_API_KEY from the environment, else the mock.
`embedder_id` names the effective embedder so stored vectors and query vectors are never mixed."""
from __future__ import annotations
import hashlib, math, os, re
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Dict, Iterator, List, Optional
from . import providers
from .locale import LOCALES, text as locale_text
from .providers import LLMError, ProviderError  # noqa: F401 (re-exported)

DEFAULT_MODEL = "text-embedding-3-small"
MOCK_DIMS = 512
_TOKEN = re.compile(r"\w+", re.UNICODE)


# Stop words of every supported language (app/locales).
STOP = frozenset(w for lang in LOCALES for w in locale_text(lang, "embeddings.stop_words").split())


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf): return w[:-len(suf)]
    return w


def mock_embed(text: str, dims: int = MOCK_DIMS) -> List[float]:
    """Feature-hashed bag of stemmed words without stop words, L2-normalised: deterministic, offline, and texts that
    share content words score higher (enough to exercise retrieval end to end; not a semantic model)."""
    v = [0.0] * dims
    for w in _TOKEN.findall(text.lower()):
        if w in STOP: continue
        v[int.from_bytes(hashlib.blake2b(_stem(w).encode(), digest_size=4).digest(), "big") % dims] += 1.0
    n = math.sqrt(sum(x * x for x in v)) or 1.0
    return [x / n for x in v]


def effective(model: str | None, cred: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The credential whose provider embeds, or None for the mock (no credential and no OPENAI_API_KEY)."""
    if cred is not None:
        p = providers.get(cred.get("provider") or "")
        if p is None or not p.supports_embeddings: raise ProviderError("PROVIDER_EMBEDDINGS_UNSUPPORTED", cred.get("provider") or "?")
        return cred
    key = os.environ.get("OPENAI_API_KEY")
    return {"provider": "openai", "api_key": key, "base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")} if key else None


def default_model(cred: Optional[Dict[str, Any]]) -> str:
    """Embedding model used when a knowledge base names none: the provider's default."""
    p = providers.get((cred or {}).get("provider") or "openai")
    return (p.default_embedding_model if p else "") or DEFAULT_MODEL


def embedder_id(model: str | None, cred: Optional[Dict[str, Any]]) -> str:
    """`<provider>:<model>` (e.g. `ollama:nomic-embed-text`) or `mock:<dims>`: stored and query vectors must come from the same one."""
    c = effective(model, cred)
    return f"{c['provider']}:{model or default_model(c)}" if c else f"mock:{MOCK_DIMS}"


# Usage of provider embeddings: observers see every call (metrics, including ingestion outside a run); the sink set by
# `collect` sees the calls made inside one node (a Retriever node, an agent's knowledge tool) so the run counts them.
UsageReport = Callable[[Dict[str, Any]], None]
_observers: List[UsageReport] = []
_sink: ContextVar[Optional[UsageReport]] = ContextVar("embedding_usage_sink", default=None)
SOURCES = ("ingest", "query")


def observe(fn: UsageReport) -> None:
    """fn(usage) for every provider embedding call: a usage record with `kind: embedding` and `source` (ingest or query)."""
    if fn not in _observers: _observers.append(fn)


def unobserve(fn: UsageReport) -> None:
    if fn in _observers: _observers.remove(fn)


@contextmanager
def collect(report: Optional[UsageReport]) -> Iterator[None]:
    """Send the usage of embedding calls made inside this block to `report` (the node's usage sink)."""
    token = _sink.set(report)
    try: yield
    finally: _sink.reset(token)


def embed(texts: List[str], model: str | None = None, cred: Optional[Dict[str, Any]] = None, source: str = "ingest") -> List[List[float]]:
    c = effective(model, cred)
    if c is None: return [mock_embed(t) for t in texts]  # the mock costs nothing and reports nothing
    vectors, usage = providers.get(c["provider"]).embed_with_usage(texts, model or default_model(c), c)
    rec = {**usage, "source": source if source in SOURCES else "ingest"}
    for fn in list(_observers):
        try: fn(rec)
        except Exception: pass  # metrics never fail an embedding call
    sink = _sink.get()
    if sink is not None: sink(usage)
    return vectors


def cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na, nb = math.sqrt(sum(x * x for x in a)), math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0
