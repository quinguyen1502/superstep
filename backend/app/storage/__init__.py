"""Where chat attachment bytes live (TASK-0191, REQ-0080, DEC-0074).

One port, `AttachmentStore`, and one backend per place: `db` (the `chat_attachments.data` column, the default), `fs` (a
folder) and `s3` (S3-compatible object storage). `STUDIO_ATTACHMENT_STORAGE` picks where new files go; each row says
where its bytes are (`storage`, `key`), so files of another backend stay readable until they are migrated.
Adapters only: this package imports `core` and nothing above it (DEC-0009).
"""
from .base import CHUNK, AttachmentStore, StoreError
from .registry import Stores, default

__all__ = ["CHUNK", "AttachmentStore", "StoreError", "Stores", "default"]
