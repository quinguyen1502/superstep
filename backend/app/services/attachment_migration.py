"""Moving chat attachment bytes between backends (TASK-0194, REQ-0080, DEC-0074).

Each file is copied, read back and checked (size and SHA-256), then its row is switched in one update, then the old copy
is deleted. A stop at any point leaves every file readable: before the switch the row still points at the old copy (a
new copy without a row is an orphan the sweep removes); after it, at the new one (an old object left behind is likewise
swept). Running again picks up what is left, and is a no-op when nothing is."""
from __future__ import annotations
import hashlib
from typing import Optional
from ..core import config, permissions as P
from ..core.errors import AppError
from ..repositories.chat_attachments import ChatAttachmentRepository
from ..storage import StoreError, Stores
from ..storage.registry import NAMES
from .attachment_files import key_for

MAX_BATCH = 1000


class AttachmentMigration:
    def __init__(self, repo: ChatAttachmentRepository, stores: Stores, access=None):
        self.repo, self.stores, self.access = repo, stores, access

    def require(self, uid: str) -> "AttachmentMigration":
        """Admins only (the HTTP route); the server-side `app.admin_cmd` runs without a user."""
        self.access.require(uid, P.ORG_MANAGE); return self

    def summary(self) -> dict:
        """Where new files go and how many files and bytes each backend holds."""
        return {"current": config.attachment_storage(), "by_storage": self.repo.by_storage()}

    def run(self, to: str, batch: int = 100, dry_run: bool = False, limit: Optional[int] = None) -> dict:
        """Moves files to `to` in batches of `batch`; at most `limit` files when given. Failed files stay where they are."""
        if to not in NAMES: raise AppError("ATTACHMENT_MIGRATE_TARGET", target=to, allowed=", ".join(NAMES))
        if not 1 <= batch <= MAX_BATCH: raise AppError("ATTACHMENT_MIGRATE_BATCH", max=MAX_BATCH)
        try: target = self.stores.get(to); probe = target.probe()
        except StoreError as e: probe = {"ok": False, "reason": e.reason}
        if not probe["ok"]: raise AppError("CHAT_ATTACHMENT_STORAGE", reason=probe["reason"])
        out = {"to": to, "dry_run": dry_run, "moved": 0, "bytes": 0, "failed": [], "pending": 0}
        if dry_run:
            out["pending"] = self._pending(to, target)
            return out
        failed: list[str] = []
        while limit is None or out["moved"] < limit:
            size = batch if limit is None else min(batch, limit - out["moved"])
            rows = self.repo.not_on(to, size, tuple(failed), target.location)
            if not rows: break
            for r in rows:
                reason = self._move(r, target)
                if reason is None: out["moved"] += 1; out["bytes"] += r.size or 0
                else: failed.append(r.id); out["failed"].append({"id": r.id, "reason": reason})
        out["pending"] = self._pending(to, target)
        return out

    def _pending(self, to: str, target) -> int:
        return self.repo.count_not_on(to, target.location)

    def _move(self, r, target) -> Optional[str]:
        """None when the file now lives on `target`, else why it stays where it is."""
        try:
            data = self.stores.get(r.storage, r.location).read(r.key if r.storage != "db" else r.id)
            if r.size is not None and len(data) != r.size: return "size does not match the stored file"
            digest = hashlib.sha256(data).hexdigest()
            key = None if target.inline else key_for(r.workflow_id, r.session_id, r.id)
            if not target.inline:
                target.put(key, data, r.mime)
                back = target.read(key)
                if len(back) != len(data) or hashlib.sha256(back).hexdigest() != digest:
                    target.delete(key); return "checksum does not match after the copy"
        except StoreError as e:
            return "missing on its backend" if e.missing else e.reason
        if not self.repo.switch(r.id, r.storage, to=target.name, key=key, data=data if target.inline else b"",
                                frm_location=r.location, location=None if target.inline else target.location):
            if key: self._quiet_delete(target, key)  # the file was deleted meanwhile
            return "the file changed during the move"
        if r.storage != "db": self._quiet_delete(self.stores.get(r.storage, r.location), r.key)
        return None

    @staticmethod
    def _quiet_delete(store, key) -> None:
        try: store.delete(key)
        except StoreError: pass  # left for the orphan sweep
