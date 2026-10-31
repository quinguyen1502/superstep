"""Chat attachment bytes in and out of a backup archive (TASK-0194, REQ-0080, DEC-0074).

`db` files travel inside the database dump, so only external backends (`fs`, `s3`) export anything: a tar stream with
one `attachments/<key>` member per file a row points at. Import writes those members back to the configured backend,
again only for keys a row of that backend names, so an archive cannot plant arbitrary objects."""
from __future__ import annotations
import io, tarfile, time
from typing import BinaryIO
from ..repositories.chat_attachments import ChatAttachmentRepository
from ..storage import Stores
from ..storage.base import PROBE_PREFIX

PREFIX = "attachments/"


class AttachmentArchive:
    def __init__(self, repo: ChatAttachmentRepository, stores: Stores):
        self.repo, self.stores = repo, stores

    def export(self, out: BinaryIO) -> int:
        """Writes the current backend's files as a tar stream to `out`; the number of files."""
        store, n = self.stores.current(), 0
        with tarfile.open(fileobj=out, mode="w|") as tar:
            if store.inline: return 0
            for key, _created in self.repo.keys(store.name):
                if not key or key.startswith(PROBE_PREFIX): continue
                data = store.read(key)
                info = tarfile.TarInfo(PREFIX + key); info.size, info.mtime, info.mode = len(data), int(time.time()), 0o600
                tar.addfile(info, io.BytesIO(data)); n += 1
        return n

    def restore(self, src: BinaryIO) -> int:
        """Writes the files of a tar stream to the current backend; the number written."""
        store, n = self.stores.current(), 0
        if store.inline: return 0
        wanted = {k for k, _c in self.repo.keys(store.name) if k}
        with tarfile.open(fileobj=src, mode="r|") as tar:
            for info in tar:
                key = info.name[len(PREFIX):] if info.name.startswith(PREFIX) else None
                if not info.isfile() or key not in wanted: continue
                handle = tar.extractfile(info)
                if handle is None: continue
                store.put(key, handle.read(), "application/octet-stream"); n += 1
        return n
