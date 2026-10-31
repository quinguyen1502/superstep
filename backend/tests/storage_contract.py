"""The contract every attachment storage backend passes (TASK-0191, REQ-0080): db, fs, s3, and the in-memory fake the
service tests use. `ready(key)` prepares a key where the backend needs it (the db backend's rows)."""
import io, time
import pytest
from app.storage import CHUNK, AttachmentStore, StoreError
from app.storage.base import as_bytes


class MemStore(AttachmentStore):
    """An external backend in memory, for service tests (write order, sweeps, failures)."""
    name = "mem"
    def __init__(self): self.objects, self.fail_put = {}, False
    def put(self, key, data, mime):
        if self.fail_put: raise StoreError("bucket unreachable")
        self.objects[key] = (bytes(as_bytes(data)), time.time())
    def open(self, key):
        if key not in self.objects: raise StoreError("not found", missing=True)
        d = self.objects[key][0]; return iter([d[i:i + CHUNK] for i in range(0, len(d), CHUNK)] or [b""])
    def delete(self, key): self.objects.pop(key, None)
    def exists(self, key): return key in self.objects
    def iter_keys(self): return iter([(k, t) for k, (_d, t) in self.objects.items()])


def check(store: AttachmentStore, ready=lambda key: None, prefix="w1/s1/"):
    big = bytes(range(256)) * ((3 * CHUNK) // 256 + 7)  # several pieces, not a multiple of CHUNK
    k1, k2 = f"{prefix}a1", f"{prefix}a2"
    for k in (k1, k2): ready(k)
    store.put(k1, big, "application/pdf"); store.put(k2, b"" if not store.inline else b"y", "text/plain")
    pieces = list(store.open(k1))
    assert b"".join(pieces) == big and all(len(p) <= CHUNK for p in pieces) and len(pieces) > 1
    assert store.read(k2) == (b"" if not store.inline else b"y")  # an empty object (db rows always hold a file)
    ready(f"{prefix}a3"); store.put(f"{prefix}a3", io.BytesIO(big), "application/pdf")  # a file, as an upload is (TASK-0200)
    assert store.read(f"{prefix}a3") == big; store.delete(f"{prefix}a3")
    assert store.exists(k1)
    store.put(k1, b"replaced", "text/plain"); assert store.read(k1) == b"replaced"  # a second put overwrites
    keys = dict(store.iter_keys())
    assert k1 in keys and isinstance(keys[k1], float) and keys[k1] <= time.time() + 5
    store.delete(k1); store.delete(k1)  # twice: a missing key is not an error
    assert not store.exists(k1)
    with pytest.raises(StoreError) as e: b"".join(store.open(k1))
    assert e.value.missing
    p = store.probe(); assert p == {"ok": True, "reason": None}, p
    store.delete(k2)
