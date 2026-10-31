"""Chat attachment bytes in and out of a backup archive (TASK-0194, REQ-0080, DEC-0074).

`db` files travel inside the database dump, so only external backends export anything: a tar stream with one
`attachments/<key>` member per file a row of those backends points at (`fs` always; `s3` when asked, since a bucket is
usually backed up on its own). Import writes each member to the backend its row names, and only for keys a row names,
so an archive cannot plant arbitrary objects."""
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

    def export(self, out: BinaryIO, backends: tuple = ("fs",)) -> int:
        """Writes the files kept on `backends` as a tar stream to `out`; the number of files."""
        n = 0
        with tarfile.open(fileobj=out, mode="w|") as tar:
            for name in backends:
                if name == "db" or name not in self.repo.storages(): continue
                store = self.stores.get(name)
                for key, _created in self.repo.keys(name):
                    if not key or key.startswith(PROBE_PREFIX): continue
                    data = store.read(key)
                    info = tarfile.TarInfo(PREFIX + key); info.size, info.mtime, info.mode = len(data), int(time.time()), 0o600
                    tar.addfile(info, io.BytesIO(data)); n += 1
        return n

    def restore(self, src: BinaryIO) -> int:
        """Writes the files of a tar stream to the backends their rows name; the number written."""
        wanted = {k: name for name in self.repo.storages() if name != "db" for k, _c in self.repo.keys(name) if k}
        n = 0
        with tarfile.open(fileobj=src, mode="r|") as tar:
            for info in tar:
                key = info.name[len(PREFIX):] if info.name.startswith(PREFIX) else None
                if not info.isfile() or key not in wanted: continue
                handle = tar.extractfile(info)
                if handle is None: continue
                self.stores.get(wanted[key]).put(key, handle, "application/octet-stream"); n += 1  # streamed (TASK-0200)
        return n
