"""The `fs` backend (TASK-0192, REQ-0080, DEC-0074): a folder, `STUDIO_ATTACHMENT_FS_PATH` (default
/data/attachments). In the all-in-one image that is the data volume; in the full stack `api` and `worker` mount the
same volume at /data. Keys are relative paths made by the service; anything that would leave the folder is refused.
Writes go to a temporary file in the same folder, then replace the target, so a reader never sees half a file."""
from __future__ import annotations
import os, re, tempfile
from pathlib import Path
from typing import Iterator
from .base import CHUNK, AttachmentStore, Data, StoreError, pieces

_PART = re.compile(r"^[A-Za-z0-9_.-]+$")


class FsStore(AttachmentStore):
    name = "fs"

    def __init__(self, root: str, protected: tuple = ()):
        self.root = Path(root).resolve()
        self.location = str(self.root)
        self.protected = tuple(Path(p).resolve() for p in protected)

    def unsafe(self) -> str | None:
        """The folder must not be, or hold, the studio's own data (database file, secret key, imports): the orphan sweep
        would otherwise run over them (TASK-0203)."""
        for p in self.protected:
            if p == self.root or self.root in p.parents:
                return "the attachment folder must not be or contain the data folder; use a subfolder such as /data/attachments"
        return None

    def _path(self, key: str) -> Path:
        parts = key.split("/")
        if not key or any(p in ("", ".", "..") or not _PART.match(p) for p in parts): raise StoreError("invalid key")
        p = self.root.joinpath(*parts).resolve()
        if self.root not in p.parents: raise StoreError("invalid key")
        return p

    def put(self, key: str, data: Data, mime: str) -> None:
        bad = self.unsafe()
        if bad: raise StoreError(bad)
        p = self._path(key)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=p.parent, prefix=".part-")
            try:
                with os.fdopen(fd, "wb") as f:
                    for piece in pieces(data): f.write(piece)
                    f.flush(); os.fsync(f.fileno())
                os.replace(tmp, p)
            except BaseException:
                Path(tmp).unlink(missing_ok=True); raise
        except OSError as e: raise StoreError(f"cannot write to the attachment folder ({e.strerror or type(e).__name__})")

    def open(self, key: str) -> Iterator[bytes]:
        p = self._path(key)
        try: f = p.open("rb")
        except FileNotFoundError: raise StoreError("not found", missing=True)
        except OSError as e: raise StoreError(f"cannot read the attachment folder ({e.strerror or type(e).__name__})")
        def chunks():
            with f:
                while piece := f.read(CHUNK): yield piece
        return chunks()

    def read(self, key: str) -> bytes:
        return b"".join(self.open(key))

    def delete(self, key: str) -> None:
        p = self._path(key)
        try: p.unlink(missing_ok=True)
        except OSError as e: raise StoreError(f"cannot delete from the attachment folder ({e.strerror or type(e).__name__})")
        for d in list(p.parents):  # empty session and workflow folders go too
            if d == self.root or self.root not in d.parents: break
            try: d.rmdir()
            except OSError: break

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def iter_keys(self) -> Iterator[tuple[str, float]]:
        if not self.root.is_dir(): return iter(())
        def walk():
            for dirpath, _dirs, files in os.walk(self.root):
                for n in files:
                    if n.startswith(".part-"): continue
                    p = Path(dirpath) / n
                    try: yield p.relative_to(self.root).as_posix(), p.stat().st_mtime
                    except OSError: continue
        return walk()
