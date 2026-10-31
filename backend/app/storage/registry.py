"""The configured backends (TASK-0191). New files go to `config.attachment_storage()`; a row's own `storage` decides
where its bytes are read from, so every backend a row names must still be reachable."""
from __future__ import annotations
import threading, time
from typing import Callable, Dict
from ..core import config
from .base import AttachmentStore, StoreError

NAMES = ("db", "fs", "s3")


class Stores:
    def __init__(self, factories: Dict[str, Callable[[], AttachmentStore]]):
        self.factories, self._built, self._lock = factories, {}, threading.Lock()
        self._status: tuple[float, dict] | None = None

    def get(self, name: str) -> AttachmentStore:
        if name not in self._built:
            with self._lock:
                if name not in self._built:
                    make = self.factories.get(name)
                    if make is None: raise StoreError(f"unknown attachment storage '{name}' (use {', '.join(NAMES)})")
                    self._built[name] = make()
        return self._built[name]

    def current(self) -> AttachmentStore:
        return self.get(config.attachment_storage())

    def status(self, max_age: float = 0) -> dict:
        """{"backend", "ok", "reason"} of the backend new files go to, for /api/health and `doctor`. With `max_age`,
        a probe younger than that is reused (health checks run often; a probe is three requests to a bucket)."""
        if max_age and self._status and time.time() - self._status[0] < max_age and self._status[1]["backend"] == config.attachment_storage():
            return self._status[1]
        out = self._probe(); self._status = (time.time(), out); return out

    def _probe(self) -> dict:
        name = config.attachment_storage()
        try: r = self.get(name).probe()
        except StoreError as e: r = {"ok": False, "reason": e.reason}
        return {"backend": name, **r}


def default(rows) -> Stores:
    """Every backend this build knows; each is built on first use from its STUDIO_ATTACHMENT_* settings."""
    from .db import DbStore
    from .s3 import S3Store
    return Stores({"db": lambda: DbStore(rows), "s3": lambda: S3Store(**config.attachment_s3())})
