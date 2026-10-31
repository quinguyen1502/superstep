"""TASK-0193 (REQ-0080, DEC-0074): the `s3` backend. Against MinIO (CI job "Attachment storage on MinIO", or any
S3-compatible endpoint in STUDIO_TEST_S3_*) it passes the shared contract and serves chat files end to end; offline, its
errors never carry the endpoint, bucket, key or credentials."""
import os, uuid
import pytest
from app.api import deps
from app.storage import StoreError
from tests.storage_contract import check

boto3 = pytest.importorskip("boto3")
from botocore.exceptions import ClientError, EndpointConnectionError  # noqa: E402
from app.storage.s3 import S3Store  # noqa: E402

LIVE = {k: os.environ.get(f"STUDIO_TEST_S3_{k}", "") for k in ("ENDPOINT", "BUCKET", "ACCESS_KEY_ID", "SECRET_ACCESS_KEY")}
live = pytest.mark.skipif(not (LIVE["ENDPOINT"] and LIVE["BUCKET"]), reason="no S3-compatible test endpoint (STUDIO_TEST_S3_ENDPOINT)")
SECRET = "sk-very-secret-value"


def minio(prefix):
    return S3Store(LIVE["BUCKET"], prefix=prefix, endpoint=LIVE["ENDPOINT"], region="us-east-1", access_key=LIVE["ACCESS_KEY_ID"],
                   secret_key=LIVE["SECRET_ACCESS_KEY"], path_style=True)


@pytest.fixture(autouse=True)
def no_read_limit(monkeypatch): monkeypatch.setenv("STUDIO_PUBLIC_CHAT_RATE_READ", "0")


# ---- against MinIO ----
@live
def test_s3_backend_contract():
    check(minio(f"contract-{uuid.uuid4().hex[:8]}"))


@live
def test_prefixes_keep_installs_apart():
    a, b = minio(f"a-{uuid.uuid4().hex[:6]}"), minio(f"b-{uuid.uuid4().hex[:6]}")
    a.put("w/s/x", b"one", "text/plain")
    assert not b.exists("w/s/x") and [k for k, _t in a.iter_keys()] == ["w/s/x"]
    a.delete("w/s/x")


@live
def test_a_chat_file_on_s3_end_to_end(monkeypatch):
    from tests.test_chat_attachments import public_session, up
    from tests.chat_files import pdf
    from tests.test_chat_sessions import c
    prefix = f"e2e-{uuid.uuid4().hex[:8]}"
    env = {"STORAGE": "s3", "S3_BUCKET": LIVE["BUCKET"], "S3_ENDPOINT": LIVE["ENDPOINT"], "S3_REGION": "us-east-1", "S3_PREFIX": prefix,
           "S3_ACCESS_KEY_ID": LIVE["ACCESS_KEY_ID"], "S3_SECRET_ACCESS_KEY": LIVE["SECRET_ACCESS_KEY"], "S3_PATH_STYLE": "true"}
    for k, v in env.items(): monkeypatch.setenv(f"STUDIO_ATTACHMENT_{k}", v)
    deps._attachment_stores.cache_clear()
    try:
        _tok, wid, _slug, v, sid, url = public_session()
        a = up(v, url, "invoice.pdf", pdf()).json()["data"]
        assert minio(prefix).read(f"{wid}/{sid}/{a['id']}") == pdf()
        d = v.get(f"{url}/{a['id']}")
        assert d.content == pdf() and d.headers["content-disposition"].startswith("attachment;")
        assert d.headers["x-content-type-options"] == "nosniff" and d.headers["cache-control"] == "private, no-store"
        assert LIVE["ENDPOINT"] not in str(d.headers) and LIVE["BUCKET"] not in str(d.headers) and "location" not in d.headers
        h = c.get("/api/health").json()["data"]; assert h["attachment_storage"] == "s3" and h["attachment_storage_ok"] is True
        v.delete(f"{url}/{a['id']}"); assert not minio(prefix).exists(f"{wid}/{sid}/{a['id']}")
    finally: deps._attachment_stores.cache_clear()


@live
def test_wrong_credentials_fail_without_the_secret():
    s = S3Store(LIVE["BUCKET"], endpoint=LIVE["ENDPOINT"], region="us-east-1", access_key="wrong", secret_key=SECRET, path_style=True)
    p = s.probe(); assert p["ok"] is False and SECRET not in p["reason"] and LIVE["ENDPOINT"] not in p["reason"]


# ---- offline ----
class Broken:
    """A client whose every call fails like a real one would."""
    def __init__(self, exc): self.exc = exc
    def __getattr__(self, _name):
        def call(**_kw): raise self.exc
        return call


def test_errors_name_the_failure_not_the_secrets():
    denied = ClientError({"Error": {"Code": "SignatureDoesNotMatch", "Message": f"key {SECRET} at https://bucket.example"}}, "PutObject")
    s = S3Store("private-bucket", client=Broken(denied))
    with pytest.raises(StoreError) as e: s.put("w/s/a", b"x", "text/plain")
    assert e.value.reason == "S3 error SignatureDoesNotMatch"
    down = S3Store("private-bucket", client=Broken(EndpointConnectionError(endpoint_url="https://minio.internal:9000")))
    p = down.probe(); assert p == {"ok": False, "reason": "S3 unreachable (EndpointConnectionError)"}
    missing = S3Store("b", client=Broken(ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")))
    with pytest.raises(StoreError) as e: missing.open("w/s/a")
    assert e.value.missing
    missing.delete("w/s/a")  # a missing key is not an error


def test_settings_and_the_missing_extra(monkeypatch):
    with pytest.raises(StoreError) as e: S3Store("")
    assert "STUDIO_ATTACHMENT_S3_BUCKET" in e.value.reason
    with pytest.raises(StoreError): S3Store("b", client=Broken(None)).put("../x", b"x", "text/plain")
    import builtins
    real = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", lambda n, *a, **k: (_ for _ in ()).throw(ImportError(n)) if n == "boto3" else real(n, *a, **k))
    with pytest.raises(StoreError) as e: S3Store("b")
    assert "superstep-backend[s3]" in e.value.reason


def test_the_client_uses_the_settings(monkeypatch):
    seen = {}
    monkeypatch.setattr(boto3, "client", lambda svc, **kw: seen.update(kw, svc=svc) or object())
    S3Store("b", endpoint="https://acct.r2.cloudflarestorage.com", region="auto", access_key="AK", secret_key=SECRET, path_style=True)
    assert seen["svc"] == "s3" and seen["endpoint_url"] == "https://acct.r2.cloudflarestorage.com" and seen["region_name"] == "auto"
    assert seen["aws_access_key_id"] == "AK" and seen["config"].s3["addressing_style"] == "path"
    seen.clear(); S3Store("b")  # no keys: the default AWS credential chain
    assert "aws_access_key_id" not in seen and seen["endpoint_url"] is None


def test_health_reports_a_broken_bucket_without_secrets(monkeypatch):
    for k, v in {"STORAGE": "s3", "S3_BUCKET": "private-bucket", "S3_ENDPOINT": "http://127.0.0.1:9", "S3_ACCESS_KEY_ID": "AK",
                 "S3_SECRET_ACCESS_KEY": SECRET, "S3_PATH_STYLE": "1"}.items():
        monkeypatch.setenv(f"STUDIO_ATTACHMENT_{k}", v)
    deps._attachment_stores.cache_clear()
    try:
        from tests.test_chat_sessions import c
        h = c.get("/api/health").json()["data"]
        assert h["attachment_storage"] == "s3" and h["attachment_storage_ok"] is False
        assert SECRET not in str(h) and "127.0.0.1" not in str(h) and "private-bucket" not in str(h)
    finally: deps._attachment_stores.cache_clear()
