"""Tool node Code mode for the editor: what the server can run, and Test with sample state."""
from __future__ import annotations
import asyncio
from typing import Any, Optional
from ..core import config
from ..core import permissions as P
from ..core.errors import AppError
from ..engine import code_languages, code_runtime
from .access import AccessService
from .rate_limit import RateLimiter


class CodeService:
    def __init__(self, access: AccessService, limiter: RateLimiter, audit=None):
        self.access, self.limiter, self.audit = access, limiter, audit

    def runtime(self) -> dict:
        """The one source the UI reads for the Code mode: runtime, whether it can run now, image, limits and packages.
        The top-level image/packages/starter are Python's (as ); `languages` has one entry per language."""
        why = code_runtime.unavailable()
        return {"code_runtime": config.code_runtime(), "available": why is None, "problem": None if why in (None, "off", "demo") else why, "demo": config.demo_mode(),
                "image": config.code_image(), "packages": config.code_packages(), "starter": code_runtime.STARTER,
                "limits": {"memory": config.code_memory(), "cpus": config.code_cpus(), "pids": config.code_pids(),
                           "seconds": config.code_max_seconds(), "source_kb": code_runtime.SOURCE_MAX // 1024},
                "languages": [self._language(x) for x in code_languages.enabled()]}

    @staticmethod
    def _language(lang_id: str) -> dict:
        lang = code_languages.LANGUAGES[lang_id]; why = code_runtime.unavailable(lang_id)
        return {"id": lang_id, "available": why is None, "problem": None if why in (None, "off") else why,
                "image": lang.image(), "packages": lang.packages(), "starter": lang.starter}

    async def test(self, uid: str, source: str, state: Any, node: Optional[str] = None, timeout: Optional[float] = None,
                   language: str = code_languages.DEFAULT) -> dict:
        """Run unsaved source once against a sample state. Nothing is stored. A failure of the code itself is a result
        ({ok: false, error, traceback}); a server that cannot run code, or a bad request, is an error."""
        if not self.access.can(uid, P.CODE_WRITE): raise AppError("CODE_WRITE_FORBIDDEN")
        ok, retry = await self.limiter.hit(f"code-test:{uid}", config.code_test_per_minute(), 60)
        if not ok: raise AppError("RATE_LIMITED", headers={"Retry-After": str(retry)}, retry_after=retry)
        if not isinstance(state, dict): state = {}
        if config.code_runtime() == "subprocess" and self.audit is not None and code_runtime.claim_first_unisolated_call():
            self.audit.record(uid, "system.code_runtime_subprocess", "system", None, "Code nodes", runtime="subprocess")
        try: res = await asyncio.to_thread(code_runtime.run_code, source, state, node=node or "test", timeout=timeout,
                                             language=language)
        except code_runtime.CodeFailure as e: return {"ok": False, "error": e.to_dict(), **e.output}
        return {"ok": True, "value": res.value, **res.trace()}
