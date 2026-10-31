"""The `db` backend (TASK-0191): bytes in `chat_attachments.data`, today's behaviour and the default. The rows are the
objects: a key is an attachment id, and deleting the row deletes the bytes."""
from __future__ import annotations
from typing import Iterator
from .base import CHUNK, AttachmentStore, Data, StoreError, as_bytes


class DbStore(AttachmentStore):
    name, inline = "db", True

    def __init__(self, rows):
        """rows: the attachment repository (data_of, set_data, keys); passed in, not imported (DEC-0009)."""
        self.rows = rows

    def put(self, key: str, data: Data, mime: str) -> None:
        if not self.rows.set_data(key, as_bytes(data)): raise StoreError("no attachment row for this key", missing=True)

    def open(self, key: str) -> Iterator[bytes]:
        data = self.rows.data_of(key)
        if not data: raise StoreError("not found", missing=True)  # an uploaded file is never empty; delete() empties it
        return (data[i:i + CHUNK] for i in range(0, len(data), CHUNK))

    def delete(self, key: str) -> None:
        self.rows.set_data(key, b"")

    def exists(self, key: str) -> bool:
        return bool(self.rows.data_of(key))

    def iter_keys(self) -> Iterator[tuple[str, float]]:
        return iter(self.rows.keys("db"))

    def probe(self) -> dict:
        return {"ok": True, "reason": None}  # the database itself is checked by /api/health
