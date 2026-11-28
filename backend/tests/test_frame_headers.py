"""Frame headers of the all-in-one image: no studio page may be framed by another
site; a published chat page /c/{slug} may be framed by the sites in its embed_origins."""
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.dataset_share_http import DatasetShareHeaders
from app.api.static import mount_frontend


def client(tmp_path):
    (tmp_path / "index.html").write_text('<div id="root"></div>'); (tmp_path / "c").mkdir(); (tmp_path / "c" / "widget.js").write_text("1")
    app = FastAPI()

    @app.get("/api/ping")
    def ping(): return {"ok": True}
    mount_frontend(app, str(tmp_path), lambda slug: "'self' https://shop.example.com" if slug == "help" else "'none'")
    app.add_middleware(DatasetShareHeaders)
    return TestClient(app)


def test_studio_pages_refuse_frames_and_chat_pages_allow_their_sites(tmp_path):
    c = client(tmp_path)
    for path in ("/", "/workflows/abc", "/api/ping", "/c/widget.js", "/c/a/b"):
        r = c.get(path)
        assert (r.headers["x-frame-options"], r.headers["content-security-policy"]) == ("DENY", "frame-ancestors 'none'"), path
    r = c.get("/c/help?embed=1")
    assert r.status_code == 200 and '<div id="root">' in r.text and "x-frame-options" not in r.headers
    assert r.headers["content-security-policy"] == "frame-ancestors 'self' https://shop.example.com"
    assert c.get("/c/other").headers["content-security-policy"] == "frame-ancestors 'none'"
    assert c.get("/c/widget.js").text == "1"


def test_nothing_changes_without_a_built_frontend(tmp_path):
    app = FastAPI(); mount_frontend(app, str(tmp_path / "missing"), lambda slug: "'none'")

    @app.get("/api/ping")
    def ping(): return {"ok": True}
    assert "x-frame-options" not in TestClient(app).get("/api/ping").headers


def test_dataset_reader_document_is_not_indexed_cached_or_sent_as_referrer(tmp_path):
    c = client(tmp_path)
    for path in ("/dataset-view", "/dataset-view/", "/DATASET-VIEW?theme=dark"):
        r = c.get(path)
        assert r.status_code == 200 and '<div id="root">' in r.text
        assert r.headers["x-frame-options"] == "DENY"
        assert r.headers["x-robots-tag"] == "noindex"
        assert r.headers["cache-control"] == "no-store"
        assert r.headers["referrer-policy"] == "no-referrer"
    for path in ("/workflows", "/c/help", "/dataset-view-extra"):
        assert "x-robots-tag" not in c.get(path).headers
