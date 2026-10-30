"""The storage port (TASK-0191, DEC-0074 decision 1)."""
from __future__ import annotations
import time, uuid
from abc import ABC, abstractmethod
from typing import Iterator

CHUNK = 64 * 1024  # bytes per streamed piece
PROBE_PREFIX = "_probe/"


class StoreError(Exception):
    """A backend failed. `reason` is safe to show: never a key, a secret or a bucket URL."""
    def __init__(self, reason: str, missing: bool = False):
        super().__init__(reason); self.reason, self.missing = reason, missing


class AttachmentStore(ABC):
    """Bytes by key. Keys are random paths (`<workflow>/<session>/<attachment id>`), never a file name.
    `inline` backends keep the bytes on the row itself (`db`): the service writes them with the row."""
    name: str = ""
    inline: bool = False

    @abstractmethod
    def put(self, key: str, data: bytes, mime: str) -> None: ...
    @abstractmethod
    def open(self, key: str) -> Iterator[bytes]:
        """The bytes in pieces of at most CHUNK. StoreError(missing=True) when there is no such key."""
    @abstractmethod
    def delete(self, key: str) -> None:
        """Removes the key; a missing key is not an error."""
    @abstractmethod
    def exists(self, key: str) -> bool: ...
    @abstractmethod
    def iter_keys(self) -> Iterator[tuple[str, float]]:
        """(key, last modified as a Unix time) of every stored object, for the orphan sweep and migrations."""

    def read(self, key: str) -> bytes:
        return b"".join(self.open(key))

    def probe(self) -> dict:
        """Writes, reads and deletes a small object: {"ok": bool, "reason": str | None}."""
        key = f"{PROBE_PREFIX}{uuid.uuid4().hex}"; body = f"probe {time.time()}".encode()
        try:
            self.put(key, body, "text/plain")
            if self.read(key) != body: return {"ok": False, "reason": "read back different bytes"}
            self.delete(key)
            return {"ok": not self.exists(key), "reason": None if not self.exists(key) else "delete did not remove the object"}
        except StoreError as e: return {"ok": False, "reason": e.reason}
        except Exception as e: return {"ok": False, "reason": type(e).__name__}  # never the message: it may carry a URL or key
