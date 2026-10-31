"""TASK-0200: the `s3` backend uploads a file larger than one part as a multipart upload, read a part at a time, and
aborts it on any failure so the bucket keeps no incomplete parts; uploads reach the backend as a spooled file read in
pieces, with the size check before and while reading. Live tests run against MinIO (CI job "Attachment storage on
MinIO", STUDIO_TEST_S3_*); the rest use a recording client."""
import io, os, uuid
import pytest
from app.storage import StoreError

pytest.importorskip("boto3")
from app.storage.s3 import S3Store  # noqa: E402

MB = 1024 * 1024
LIVE = {k: os.environ.get(f"STUDIO_TEST_S3_{k}", "") for k in ("ENDPOINT", "BUCKET", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY")}
live = pytest.mark.skipif(not (LIVE["ENDPOINT"] and LIVE["BUCKET"]), reason="no S3-compatible test endpoint (STUDIO_TEST_S3_ENDPOINT)")


class Reader(io.RawIOBase):
    """`size` bytes of a pattern, read like an upload; reads fail once `fail_at` bytes have been read."""
    def __init__(self, size, fail_at=None): self.size, self.pos, self.fail_at, self.biggest = size, 0, fail_at, 0
    def readable(self): return True
    def read(self, n=-1):
        if self.fail_at is not None and self.pos >= self.fail_at: raise OSError("connection reset")
        n = self.size - self.pos if n is None or n < 0 else min(n, self.size - self.pos)
        self.biggest = max(self.biggest, n); out = bytes((self.pos + i) % 251 for i in range(n)) if n < 64 else (bytes(range(251)) * (n // 251 + 2))[self.pos % 251:self.pos % 251 + n]
        self.pos += n; return out


def pattern(size): return Reader(size).read(size)


class Client:
    """Records the S3 calls; `fail_part` makes that upload_part call fail."""
    def __init__(self, fail_part=None): self.calls, self.fail_part = [], fail_part
    def put_object(self, **kw): self.calls.append(("put", len(kw["Body"])))
    def create_multipart_upload(self, **kw): self.calls.append(("create", kw["ContentType"])); return {"UploadId": "u1"}
    def upload_part(self, **kw):
        if kw["PartNumber"] == self.fail_part: raise ConnectionError("reset")
        self.calls.append(("part", kw["PartNumber"], len(kw["Body"]))); return {"ETag": f"e{kw['PartNumber']}"}
    def complete_multipart_upload(self, **kw): self.calls.append(("complete", [p["PartNumber"] for p in kw["MultipartUpload"]["Parts"]]))
    def abort_multipart_upload(self, **kw): self.calls.append(("abort", kw["UploadId"]))


def test_small_files_are_one_put_and_large_ones_go_in_parts():
    c = Client(); s = S3Store("b", client=c, part_mb=5)
    s.put("k", b"x" * (5 * MB), "text/plain"); s.put("k", Reader(3 * MB), "image/png")
    assert c.calls == [("put", 5 * MB), ("put", 3 * MB)]
    c.calls.clear(); r = Reader(11 * MB + 7); s.put("k", r, "application/pdf")
    assert c.calls == [("create", "application/pdf"), ("part", 1, 5 * MB), ("part", 2, 5 * MB), ("part", 3, MB + 7), ("complete", [1, 2, 3])]
    assert r.biggest <= 5 * MB  # read a part at a time, never the whole file


@pytest.mark.parametrize("how", ["part", "read"])
def test_a_failure_aborts_the_upload(how):
    c = Client(fail_part=2 if how == "part" else None); s = S3Store("b", client=c, part_mb=5)
    data = Reader(16 * MB, fail_at=15 * MB if how == "read" else None)
    with pytest.raises(StoreError) as e: s.put("k", data, "application/pdf")
    assert c.calls[-1] == ("abort", "u1") and not any(x[0] == "complete" for x in c.calls)
    assert "reset" not in e.value.reason or "S3" in e.value.reason


def test_the_part_size_setting(monkeypatch):
    from app.core import config
    monkeypatch.setenv("STUDIO_ATTACHMENT_S3_MULTIPART_MB", "2"); assert config.attachment_s3()["part_mb"] == 5  # S3's minimum
    monkeypatch.setenv("STUDIO_ATTACHMENT_S3_MULTIPART_MB", "16"); assert config.attachment_s3()["part_mb"] == 16
    monkeypatch.delenv("STUDIO_ATTACHMENT_S3_MULTIPART_MB"); assert config.attachment_s3()["part_mb"] == 8


def test_an_upload_is_read_in_pieces_and_stopped_at_the_ceiling(monkeypatch):
    """No usable content-length (a chunked body): the size check runs while reading, not after a whole read."""
    from app.api.routes import public_chat
    from tests.test_chat_attachments import public_session, up
    seen = []
    real = public_chat.tempfile.SpooledTemporaryFile
    monkeypatch.setattr(public_chat.tempfile, "SpooledTemporaryFile", lambda **kw: seen.append(kw) or real(**kw))
    _tok, _wid, _slug, v, _sid, url = public_session()
    monkeypatch.setenv("STUDIO_CHAT_ATTACHMENT_MAX_MB", "1")  # the operator lowers the ceiling under the chat's 10 MB
    r = up(v, url, "big.png", b"\x89PNG\r\n\x1a\n" + b"x" * MB)
    assert r.json()["error"]["code"] == "CHAT_ATTACHMENT_TOO_LARGE"
    ok = up(v, url, "small.png", b"\x89PNG\r\n\x1a\n" + b"x" * 1000).json()["data"]
    assert ok["size"] == 1008 and seen


# ---- against MinIO ----
def minio(prefix):
    return S3Store(LIVE["BUCKET"], prefix=prefix, endpoint=LIVE["ENDPOINT"], region="us-east-1", access_key=LIVE["ACCESS_KEY_ID"],
                   secret_key=LIVE["SECRET_ACCESS_KEY"], path_style=True, part_mb=5)


def pending(s, key):
    r = s.client.list_multipart_uploads(Bucket=s.bucket, Prefix=s._key(key))
    return [u for u in r.get("Uploads", []) if u["Key"] == s._key(key)]


@live
def test_a_multipart_upload_on_minio():
    s = minio(f"mp-{uuid.uuid4().hex[:8]}"); size = 12 * MB + 123
    s.put("w/s/big", Reader(size), "application/pdf")
    assert s.read("w/s/big") == pattern(size) and not pending(s, "w/s/big")
    head = s.client.head_object(Bucket=s.bucket, Key=s._key("w/s/big"))
    assert head["ContentLength"] == size and head["ETag"].strip('"').endswith("-3")  # three parts
    s.delete("w/s/big")


@live
def test_a_failed_multipart_upload_leaves_nothing_on_minio():
    s = minio(f"mp-{uuid.uuid4().hex[:8]}")
    with pytest.raises(StoreError): s.put("w/s/cut", Reader(16 * MB, fail_at=11 * MB), "application/pdf")
    assert not s.exists("w/s/cut") and not pending(s, "w/s/cut")


@live
def test_a_large_chat_upload_streams_to_minio(monkeypatch):
    from app.api import deps
    from tests.test_chat_attachments import public_session, up
    prefix = f"mp-{uuid.uuid4().hex[:8]}"
    for k, v in {"STORAGE": "s3", "S3_BUCKET": LIVE["BUCKET"], "S3_PREFIX": prefix, "S3_ENDPOINT": LIVE["ENDPOINT"], "S3_REGION": "us-east-1",
                 "S3_ACCESS_KEY_ID": LIVE["ACCESS_KEY_ID"], "S3_SECRET_ACCESS_KEY": LIVE["SECRET_ACCESS_KEY"], "S3_PATH_STYLE": "1",
                 "S3_MULTIPART_MB": "5"}.items():
        monkeypatch.setenv(f"STUDIO_ATTACHMENT_{k}", v)
    monkeypatch.setenv("STUDIO_CHAT_ATTACHMENT_MAX_MB", "20")
    deps._attachment_stores.cache_clear()
    try:
        _tok, wid, slug, v, sid, url = public_session(max_mb=20)
        png = b"\x89PNG\r\n\x1a\n" + pattern(11 * MB)
        r = up(v, url, "big.png", png); assert r.status_code == 200, r.text
        a = r.json()["data"]; assert a["size"] == len(png)
        assert v.get(f"{url}/{a['id']}").content == png and not pending(minio(prefix), f"{wid}/{sid}/{a['id']}")
    finally: deps._attachment_stores.cache_clear()
