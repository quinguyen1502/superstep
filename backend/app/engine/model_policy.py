"""Opt-in LLM failover. Credentials stay owner-bound; failed attempts never publish partial text."""
from __future__ import annotations
from concurrent.futures import CancelledError
import time
from langgraph.errors import NodeTimeoutError
from .issues import Issue
from .providers import LLMError, ProviderError, get

FAILOVER_CODES = frozenset({"PROVIDER_UNREACHABLE", "PROVIDER_BAD_RESPONSE", "PROVIDER_RATE_LIMITED", "MODEL_NOT_FOUND"})


def errors(nid: str, data: dict) -> list[str]:
    fallback = data.get("fallback")
    if fallback is None: return []
    valid = isinstance(fallback, dict) and set(fallback) == {"credential_id", "model"}
    valid = valid and all(isinstance(fallback.get(k), str) and 0 < len(fallback[k].strip()) <= 200 for k in ("credential_id", "model"))
    primary_model = data.get("model") or "gpt-4o-mini"
    valid = valid and isinstance(primary_model, str) and (fallback["credential_id"], fallback["model"].strip()) != (data.get("credential_id"), primary_model.strip())
    return [] if valid else [Issue("MODEL_FALLBACK_INVALID", node=nid)]


def run(data, primary, resolve, invoke, on_token, emit, cancelled=None):
    """At most two calls per node attempt. Buffer policy output until success (ordinary nodes still stream live).

    `invoke(model, credential)` performs a non-streaming call and reports its usage. Resolve the alternate before
    starting either call, so permission/configuration errors cannot be hidden by a successful primary call.
    """
    if errors("llm", data): raise LLMError("Invalid fallback model policy")
    if resolve is None: raise LLMError("Fallback uses a credential but no resolver is available")
    alternate = resolve(data["fallback"]["credential_id"])
    for cred in (primary, alternate):
        if cred is not None and ((provider := get(cred.get("provider"))) is None or provider.kind != "chat"):
            raise LLMError("Model fallback requires chat model credentials")
    started = time.monotonic()

    def check():
        if cancelled and cancelled(): raise CancelledError("Run cancelled")
        if data.get("timeout") and (elapsed := time.monotonic() - started) >= data["timeout"]:
            raise NodeTimeoutError("llm", elapsed, kind="run", run_timeout=data["timeout"])

    choices = ((data.get("model") or "gpt-4o-mini", primary), (data["fallback"]["model"].strip(), alternate))
    for attempt, (model, cred) in enumerate(choices, 1):
        check()
        record = {"attempt": attempt, "provider": cred["provider"] if cred else "environment", "model": model}
        try: out = invoke(model, cred)
        except ProviderError as e:
            emit({**record, "status": "error", "code": e.code})
            if attempt == 2 or e.code not in FAILOVER_CODES: raise
            continue
        check()
        emit({**record, "status": "ok"})
        if on_token: on_token(out)
        return out
