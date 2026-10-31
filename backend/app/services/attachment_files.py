"""The bytes of chat attachments (TASK-0191, REQ-0080, DEC-0074): writing, reading and deleting them on the configured
backend, and the orphan sweep. Used by the attachment service (uploads, downloads) and the chat session service (the
run's file port, session delete, retention).

- Write order: the object first, then the row; a failed row write deletes the object, so a file is either fully stored
  and linked or not visible (REQ-0080 business rules). A `db` backend writes the bytes with the row.
- Delete order: the row first, then the object. A crash in between leaves an orphan, which the sweep removes once it is
  older than an hour.
"""
from __future__ import annotations
import logging, time
from typing import Iterable, Iterator, Optional
from ..core.errors import AppError
from ..models import ChatAttachment
from ..repositories import ChatAttachmentRepository
from ..storage import Stores, StoreError
from ..storage.base import PROBE_PREFIX, Data, as_bytes, is_service_key

log = logging.getLogger(__name__)
WORKER_KEY = f"{PROBE_PREFIX}worker"  # the worker's heartbeat: the api sees it only when they share the backend (TASK-0192)
ORPHAN_AGE = 3600  # an object without a row is removed once it is this old (seconds)
BATCH = 500


def key_for(workflow_id: Optional[str], session_id: str, aid: str) -> str:
    """Random, never the file name (REQ-0080)."""
    return f"{workflow_id or 'adhoc'}/{session_id}/{aid}"


def _unavailable(e: StoreError) -> AppError:
    return AppError("CHAT_ATTACHMENT_NOT_FOUND") if e.missing else AppError("CHAT_ATTACHMENT_STORAGE", reason=e.reason)


class AttachmentFiles:
    def __init__(self, repo: ChatAttachmentRepository, stores: Stores):
        self.repo, self.stores = repo, stores

    def add(self, row: ChatAttachment, workflow_id: Optional[str], data: Data) -> ChatAttachment:
        """Stores `data` (bytes, or a file from its current position) on the current backend and adds `row` pointing at it."""
        try: store = self.stores.current()
        except StoreError as e: raise _unavailable(e)
        row.storage = store.name
        if store.inline:
            row.data, row.key = as_bytes(data), None
            return self.repo.add(row)
        row.data, row.key, row.location = b"", key_for(workflow_id, row.session_id, row.id), store.location
        try: store.put(row.key, data, row.mime)
        except StoreError as e: raise _unavailable(e)
        try: return self.repo.add(row)
        except Exception:
            self._drop(row.storage, row.key, row.location); raise

    def open(self, row) -> Iterator[bytes]:
        """The bytes of a file in pieces. The first piece is read here, so a backend failure becomes an error answer
        and not a broken download."""
        try:
            it = self._store(row).open(row.key if row.storage != "db" else row.id)
            first = next(it, b"")
        except StoreError as e: raise _unavailable(e)
        def rest():
            yield first
            try: yield from it
            except StoreError as e: log.warning("attachment %s: reading failed mid-stream (%s)", row.id, e.reason)
        return rest()

    def read(self, row) -> bytes:
        return b"".join(self.open(row))

    def _store(self, row):
        """The store a row's bytes were written to: its backend, at the folder or bucket/prefix recorded on the row."""
        return self.stores.get(row.storage, getattr(row, "location", None))

    def drop(self, refs: Iterable[tuple]) -> None:
        for storage, key, *rest in refs:
            if storage != "db" and key: self._drop(storage, key, rest[0] if rest else None)

    def _drop(self, storage: str, key: str, location: Optional[str] = None) -> None:
        try: self.stores.get(storage, location).delete(key)
        except Exception as e: log.warning("attachment storage %s: delete failed (%s); the orphan sweep retries", storage, type(e).__name__)

    def remove_unsent(self, aid: str, sid: str) -> bool:
        ref = self.repo.delete_unsent(aid, sid)
        if ref is None: return False
        self.drop([ref]); return True

    def sweep_stale(self, before: float) -> int:
        refs = self.repo.delete_stale(before); self.drop(refs); return len(refs)

    def refs_of_sessions(self, sids: list[str]) -> list[tuple]:
        return self.repo.refs_of_sessions(sids)

    def backfill_locations(self) -> int:
        """Rows written before locations were recorded (0.10.1) get the folder or bucket/prefix configured now, which is
        the one they were written to as long as the setting has not changed since (TASK-0203). Run at start-up."""
        n = 0
        for name in {x for x in self.repo.storages() if x != "db"}:
            try: n += self.repo.backfill_locations(name, self.stores.get(name).location)
            except StoreError as e: log.warning("attachment storage %s: cannot record locations (%s)", name, e.reason)
        return n

    def sweep_orphans(self, now: Optional[float] = None, age: float = ORPHAN_AGE) -> int:
        """Removes objects that no row points at and that are older than `age`, on every external backend in use, at
        its configured folder or bucket/prefix only. Only keys of the service's own form are considered (TASK-0203):
        never a file of another system, of a nested install, or the studio's own data."""
        now = time.time() if now is None else now
        names = {n for n in self.repo.storages() if n != "db"}
        try:
            cur = self.stores.current()
            if not cur.inline: names.add(cur.name)
        except StoreError: pass
        n = 0
        for name in sorted(names):
            try:
                store = self.stores.get(name); batch: list[tuple[str, float]] = []
                bad = store.unsafe()
                if bad: log.warning("attachment storage %s: orphan sweep skipped (%s)", name, bad); continue
                if store.warning(): log.warning("attachment storage %s: %s", name, store.warning())
                for item in store.iter_keys():
                    batch.append(item)
                    if len(batch) >= BATCH: n += self._sweep_batch(store, batch, now - age); batch = []
                n += self._sweep_batch(store, batch, now - age)
            except Exception as e: log.warning("attachment storage %s: orphan sweep failed (%s)", name, type(e).__name__)
        return n

    def _sweep_batch(self, store, batch: list[tuple[str, float]], before: float) -> int:
        old = [k for k, t in batch if t < before and is_service_key(k)]
        known = self.repo.known(store.name, old, store.location); n = 0
        for k in old:
            if k not in known: store.delete(k); n += 1
        return n

    def status(self) -> dict:
        return self.stores.status()

    def heartbeat(self, now: Optional[float] = None) -> None:
        """The worker writes its heartbeat on the current backend (retention loop). With `fs`, an api that cannot see
        it does not share the worker's folder: files uploaded there would be missing for runs."""
        try:
            store = self.stores.current()
            if not store.inline: store.put(WORKER_KEY, str(time.time() if now is None else now).encode(), "text/plain")
        except Exception as e: log.warning("attachment storage: worker heartbeat failed (%s)", type(e).__name__)

    def worker_seen(self) -> Optional[float]:
        """Seconds since the worker's last heartbeat on the current backend, or None (never seen, or `db`)."""
        try:
            store = self.stores.current()
            if store.inline: return None
            return max(0.0, time.time() - float(store.read(WORKER_KEY).decode()))
        except Exception: return None
