"""Trusted capture write port and owner-only read port; no public upload/download URLs."""
import struct
import time
import uuid

from ..core.errors import AppError
from ..models import BrowserArtifact

RETENTION_S = 3600
MAX_PNG_BYTES = 2 * 1024 * 1024


class BrowserArtifactService:
    def __init__(self, repo, clock=time.time): self.repo, self.clock = repo, clock

    def save(self, owner, context, png):
        """Called by the authorised run service after capture; owner/context never come from tool arguments."""
        if not isinstance(png, bytes) or len(png) < 24 or len(png) > MAX_PNG_BYTES or not png.startswith(b"\x89PNG\r\n\x1a\n") or png[12:16] != b"IHDR":
            raise AppError("BROWSER_ARTIFACT_INVALID")
        width, height = struct.unpack(">II", png[16:24])
        if not 0 < width <= 1024 or not 0 < height <= 768: raise AppError("BROWSER_ARTIFACT_INVALID")
        now, artifact_id = self.clock(), uuid.uuid4().hex
        row = BrowserArtifact(id=artifact_id, owner=owner, principal_id=context.principal_id, run_id=context.run_id,
            connection_id=context.connection_id, group_id=context.group_id, created=now, expires=now + RETENTION_S, data=png)
        self.repo.add(row)
        return artifact_id

    def read(self, artifact_id, owner):
        row = self.repo.owned(artifact_id, owner, self.clock())
        if row is None: raise AppError("BROWSER_ARTIFACT_NOT_FOUND")
        return row.data

    def sweep(self): return self.repo.sweep(self.clock())
