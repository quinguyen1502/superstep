"""Per-user provider credentials (LLM, TypeSafe, SMTP; adds non-secret `settings`): create/list/delete, model list / connection test, and the run-time resolver.

Secrets are encrypted before they reach the repository and are only decrypted by `resolve()`.
Provider specifics (defaults, key requirement, headers, model listing) live in engine/providers.py."""
import json, time, uuid
from typing import Any, Callable, Dict, Optional
from ..core import crypto
from ..core.errors import AppError
from ..engine import providers as registry
from ..models import Credential
from ..repositories import CredentialRepository


def _headers(c: Credential) -> Dict[str, str]:
    try: return json.loads(c.headers) if c.headers else {}
    except ValueError: return {}


def _settings(c: Credential) -> Dict[str, Any]:
    try: return json.loads(c.settings) if c.settings else {}
    except ValueError: return {}


def public(c: Credential) -> Dict[str, Any]:
    return {"id": c.id, "name": c.name, "provider": c.provider, "base_url": c.base_url, "hint": c.hint,
            "headers": _headers(c), "settings": _settings(c), "created": c.created}


def _provider(pid: str) -> registry.Provider:
    p = registry.get(pid)
    if p is None: raise AppError("CREDENTIAL_PROVIDER_UNSUPPORTED", provider=pid)
    return p


def _clean(p: registry.Provider, api_key: str, base_url: Optional[str], headers: Optional[Dict[str, str]]):
    key, base = (api_key or "").strip(), (base_url or "").strip() or None
    if p.settings_fields: base = None  # the provider's settings say where it connects (SMTP host)
    if p.key_required and not key: raise AppError("CREDENTIAL_KEY_REQUIRED")
    if base and not base.startswith(("https://", "http://")): raise AppError("CREDENTIAL_BASE_URL_INVALID")
    hdrs = {k: v.strip() for k, v in (headers or {}).items() if v and v.strip()}
    for k in hdrs:
        if k not in p.header_fields: raise AppError("CREDENTIAL_HEADER_UNSUPPORTED", provider=p.id, header=k)
    return key, base, hdrs


def _probe(p: registry.Provider, cred: Dict[str, Any]) -> Dict[str, Any]:
    t0 = time.perf_counter()
    try: models = p.list_models(cred)
    except registry.ProviderError as e: raise AppError(e.code, **e.params) from None
    return {"ok": True, "provider": p.id, "base_url": p.base(cred, p.default_base_url), "models": models,
            "latency_ms": round((time.perf_counter() - t0) * 1000)}


class CredentialService:
    def __init__(self, repo: CredentialRepository): self.repo = repo

    @staticmethod
    def providers() -> list[dict]:
        return [p.info() for p in registry.REGISTRY.values()]

    def list(self, uid: str) -> list[dict]:
        return [public(c) for c in self.repo.list_for_owner(uid)]

    def create(self, uid: str, name: str, provider: str, api_key: str, base_url: str | None,
               headers: Optional[Dict[str, str]] = None, settings: Optional[Dict[str, Any]] = None) -> dict:
        p = _provider(provider)
        key, base, hdrs = _clean(p, api_key, base_url, headers)
        st = p.clean_settings(settings) if p.settings_fields else {}
        c = Credential(id=uuid.uuid4().hex[:10], owner=uid, name=name.strip() or provider, provider=provider, base_url=base,
                       secret=crypto.encrypt(key) if key else None, hint=crypto.mask(key) if key else "",
                       headers=json.dumps(hdrs) if hdrs else None, settings=json.dumps(st) if st else None, created=time.time())
        return public(self.repo.add(c))

    def update(self, uid: str, cid: str, name: str, base_url: str | None, headers: Optional[Dict[str, str]],
               api_key: Optional[str] = None, clear_key: bool = False, settings: Optional[Dict[str, Any]] = None) -> dict:
        """Edit name / base URL / headers / settings; the secret is kept unless a new key is entered (or cleared where optional)."""
        c = self.repo.get_owned(cid, uid)
        if c is None: raise AppError("CREDENTIAL_NOT_FOUND")
        p = _provider(c.provider)
        new_key = (api_key or "").strip()
        has_key = bool(new_key) or (bool(c.secret) and not clear_key)
        _, base, hdrs = _clean(p, new_key or ("kept" if has_key else ""), base_url, headers)
        values: Dict[str, Any] = {"name": name.strip() or c.provider, "base_url": base, "headers": json.dumps(hdrs) if hdrs else None}
        if p.settings_fields and settings is not None: values["settings"] = json.dumps(p.clean_settings(settings))  # omitted = kept
        if new_key: values.update(secret=crypto.encrypt(new_key), hint=crypto.mask(new_key))
        elif not has_key: values.update(secret=None, hint="")
        return public(self.repo.update_owned(cid, uid, **values))

    def embedding_test(self, uid: str, cid: str, model: Optional[str]) -> dict:
        """Embed a probe text with the credential: proves the embedding model works and reports its dimension."""
        cred = self.resolve(uid, cid); p = _provider(cred["provider"])
        if not p.supports_embeddings: raise AppError("PROVIDER_EMBEDDINGS_UNSUPPORTED", provider=p.id)
        m = (model or "").strip() or p.default_embedding_model
        t0 = time.perf_counter()
        try: vec = p.embed(["connection test"], m, cred)[0]
        except registry.ProviderError as e: raise AppError(e.code, **e.params) from None
        return {"ok": True, "model": m, "dims": len(vec), "latency_ms": round((time.perf_counter() - t0) * 1000)}

    def delete(self, cid: str, uid: str) -> dict:
        if not self.repo.delete_owned(cid, uid): raise AppError("CREDENTIAL_NOT_FOUND")
        return {"ok": True}

    def probe(self, provider: str, api_key: str, base_url: str | None, headers: Optional[Dict[str, str]],
              uid: Optional[str] = None, credential_id: Optional[str] = None, settings: Optional[Dict[str, Any]] = None) -> dict:
        """Test unsaved settings: lists the provider's models (success = reachable + authorised).
        While editing, an empty key means the stored one of `credential_id` (owner only)."""
        p = _provider(provider)
        if not (api_key or "").strip() and credential_id and uid: api_key = self.resolve(uid, credential_id)["api_key"]
        key, base, hdrs = _clean(p, api_key, base_url, headers)
        st = p.clean_settings(settings) if p.settings_fields else {}
        return _probe(p, {"provider": p.id, "api_key": key, "base_url": base, "headers": hdrs, "settings": st})

    def models(self, uid: str, cid: str) -> dict:
        """Model list / connection test for a saved credential."""
        cred = self.resolve(uid, cid)
        return _probe(_provider(cred["provider"]), cred)

    def resolve(self, uid: str, cid: str) -> Dict[str, Any]:
        """Decrypted credential for runtime use only. Raises CREDENTIAL_NOT_FOUND if missing or not owned."""
        c = self.repo.get_owned(cid, uid)
        if c is None: raise AppError("CREDENTIAL_NOT_FOUND", details={"credential_id": cid})
        p = _provider(c.provider)
        return {"provider": c.provider, "base_url": c.base_url or p.default_base_url,
                "api_key": crypto.decrypt(c.secret) if c.secret else "", "headers": _headers(c), "settings": _settings(c), "name": c.name}

    def resolver(self, uid: str) -> Callable[[str], Dict[str, Any]]:
        """Credential lookup bound to one user, handed to the run engine (`run_stream(resolve=...)`)."""
        return lambda cid: self.resolve(uid, cid)
