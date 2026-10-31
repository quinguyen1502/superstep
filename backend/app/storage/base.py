"""The storage port (TASK-0191, DEC-0074 decision 1)."""
from __future__ import annotations
import re, time, uuid
from abc import ABC, abstractmethod
from typing import BinaryIO, Iterator, Union

CHUNK = 64 * 1024  # bytes per streamed piece
PROBE_PREFIX = "_probe/"


Data = Union[bytes, BinaryIO]  # put() takes the bytes or a readable, seekable file (an upload spooled to disk, TASK-0200)


def as_bytes(data: Data) -> bytes:
    """All of `data`: for a backend that keeps the bytes whole (`db`)."""
    return data if isinstance(data, (bytes, bytearray)) else data.read()


def pieces(data: Data, size: int = CHUNK) -> Iterator[bytes]:
    """`data` in pieces of at most `size` bytes, without reading a file whole."""
    if isinstance(data, (bytes, bytearray)):
        for i in range(0, len(data), size): yield bytes(data[i:i + size])
        return
    while piece := data.read(size): yield piece


class StoreError(Exception):
    """A backend failed. `reason` is safe to show: never a key, a secret or a bucket URL."""
    def __init__(self, reason: str, missing: bool = False):
        super().__init__(reason); self.reason, self.missing = reason, missing


KEY_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}/[A-Za-z0-9_-]{1,128}/[0-9a-f]{32}$")  # <workflow|adhoc>/<session>/<attachment id>


def is_service_key(key: str) -> bool:
    """A key the attachment service makes (TASK-0203). The orphan sweep deletes nothing else, so files of other systems
    or of an install under a nested folder or prefix are never touched."""
    return bool(KEY_RE.match(key or ""))


class AttachmentStore(ABC):
    """Bytes by key. Keys are random paths (`<workflow>/<session>/<attachment id>`), never a file name.
    `inline` backends keep the bytes on the row itself (`db`): the service writes them with the row."""
    name: str = ""
    inline: bool = False
    location: str = ""  # where this store keeps objects (folder, or bucket/prefix); recorded on each row (TASK-0203)

    def unsafe(self) -> str | None:
        """Why this configuration must not be used (nothing is written or swept there), or None."""
        return None

    def warning(self) -> str | None:
        """A risky but allowed configuration, logged by the sweep, or None."""
        return None

    @abstractmethod
    def put(self, key: str, data: Data, mime: str) -> None:
        """Writes `data` (bytes, or a file read from its current position to the end) under `key`."""
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
        bad = self.unsafe()
        if bad: return {"ok": False, "reason": bad}
        key = f"{PROBE_PREFIX}{uuid.uuid4().hex}"; body = f"probe {time.time()}".encode()
        try:
            self.put(key, body, "text/plain")
            if self.read(key) != body: return {"ok": False, "reason": "read back different bytes"}
            self.delete(key)
            return {"ok": not self.exists(key), "reason": None if not self.exists(key) else "delete did not remove the object"}
        except StoreError as e: return {"ok": False, "reason": e.reason}
        except Exception as e: return {"ok": False, "reason": type(e).__name__}  # never the message: it may carry a URL or key
