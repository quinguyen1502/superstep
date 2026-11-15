"""knowledge bases (upload txt/md/pdf, chunk, embed, search) and the Retriever node."""
import os, uuid
os.environ.pop("OPENAI_API_KEY", None)
import httpx
from fastapi.testclient import TestClient
from app.engine import documents, embeddings, llm
from app.engine.ports import Ports
from app.engine.runtime import run_stream
from app.engine.validator import validate
from app.main import app

H = lambda t: {"Authorization": f"Bearer {t}"}
FAQ = """Shipping\n\nOrders ship within two business days from our Hanoi warehouse.\n\nRefunds\n\nRefunds are issued to the original card within 7 days after we receive the return."""


def pdf_bytes(text: str) -> bytes:
    """A minimal one-page PDF with `text` (Helvetica), enough for pypdf to extract."""
    stream = f"BT /F1 12 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>",
            b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = b"%PDF-1.4\n", []
    for i, o in enumerate(objs, 1): offs.append(len(out)); out += b"%d 0 obj\n" % i + o + b"\nendobj\n"
    x = len(out); out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1) + b"".join(b"%010d 00000 n \n" % o for o in offs)
    return out + b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, x)


def user(c):
    email = f"kb{uuid.uuid4().hex[:6]}@example.com"
    c.post("/api/auth/register", json={"email": email, "password": "secret123"})
    return c.post("/api/auth/login", json={"email": email, "password": "secret123"}).json()["data"]["token"]


def test_mock_embedding_is_deterministic_and_semantic_enough():
    a, b = embeddings.mock_embed("refund to card"), embeddings.mock_embed("refund to card")
    assert a == b and len(a) == embeddings.MOCK_DIMS
    q = embeddings.mock_embed("how do refunds work")
    assert embeddings.cosine(q, embeddings.mock_embed("Refunds are issued to the card")) > embeddings.cosine(q, embeddings.mock_embed("Orders ship from Hanoi"))
    assert embeddings.embedder_id(None, None) == "mock:512"


def test_chunking_and_extraction():
    parts = documents.chunk("a " * 1000)
    assert len(parts) > 1 and all(len(p) <= documents.CHUNK_CHARS for p in parts)
    assert documents.chunk("one\n\ntwo") == ["one\n\ntwo"]
    assert "Hello PDF" in documents.extract("x.pdf", pdf_bytes("Hello PDF"))
    assert documents.extract("x.md", "# Überschrift café".encode()) == "# Überschrift café"


def test_openai_embeddings_request(monkeypatch):
    seen = {}
    def handler(req):
        seen["url"], seen["auth"], body = str(req.url), req.headers["authorization"], __import__("json").loads(req.content)
        return httpx.Response(200, json={"data": [{"index": i, "embedding": [float(i), 1.0]} for i, _ in enumerate(body["input"])]})
    monkeypatch.setattr(llm.providers, "http_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    cred = {"provider": "openai", "api_key": "sk-test", "base_url": "https://example.test/v1"}
    assert embeddings.embed(["a", "b"], None, cred) == [[0.0, 1.0], [1.0, 1.0]]
    assert seen["url"] == "https://example.test/v1/embeddings" and seen["auth"] == "Bearer sk-test"
    assert embeddings.embedder_id(None, cred) == "openai:text-embedding-3-small"


def retriever_wf(kb="kb1", **d):
    return {"name": "rag", "state": [{"name": "question", "type": "string"}, {"name": "context", "type": "list"}],
            "nodes": [{"id": "start", "type": "start", "data": {}},
                      {"id": "r", "type": "retriever", "data": {"label": "Retrieve", "knowledge_base_id": kb, "query": "{{state.question}}", "top_k": 2,
                                                                 "output_field": "context", **d}},
                      {"id": "end", "type": "end", "data": {}}],
            "edges": [{"id": "1", "source": "start", "target": "r"}, {"id": "2", "source": "r", "target": "end"}]}


def test_retriever_validation_and_engine():
    assert validate(retriever_wf()) == []
    assert any("choose a knowledge base" in x for x in validate(retriever_wf(kb="")))
    assert any("top_k must be 1-20" in x for x in validate(retriever_wf(top_k=50)))
    calls = []
    ports = Ports(retrieve=lambda kb, q, k: calls.append((kb, q, k)) or [{"text": "hit", "score": 1.0}])
    evs = list(run_stream(retriever_wf(), {"question": "refund?"}, ports=ports))
    assert evs[-1]["type"] == "run_finished" and evs[-1]["state"]["context"] == [{"text": "hit", "score": 1.0}]
    assert calls == [("kb1", "refund?", 2)]
    evs = list(run_stream(retriever_wf(), {"question": "x"}))  # no service wired: a clear node error
    assert evs[-1]["type"] == "error" and evs[-1]["node"] == "r"


def test_api_upload_search_and_run():
    c = TestClient(app); tok = user(c)
    assert c.post("/api/knowledge-bases", json={"name": " "}, headers=H(tok)).json()["error"]["code"] == "KB_NAME_REQUIRED"
    kb = c.post("/api/knowledge-bases", json={"name": "FAQ"}, headers=H(tok)).json()["data"]
    assert kb["model"] == "text-embedding-3-small" and kb["embedder"] is None
    up = lambda name, data: c.post(f"/api/knowledge-bases/{kb['id']}/documents", files={"file": (name, data)}, headers=H(tok)).json()
    assert up("faq.md", FAQ.encode())["data"]["chunks"] == 1
    assert up("policy.pdf", pdf_bytes("Warranty covers two years for laptops"))["success"]
    assert up("x.docx", b"x")["error"]["code"] == "KB_FILE_TYPE_UNSUPPORTED"
    assert up("big.txt", b"a" * (10 * 1024 * 1024 + 1))["error"]["code"] == "KB_FILE_TOO_LARGE"
    assert up("blank.txt", b"  \n ")["error"]["code"] == "KB_FILE_EMPTY"
    got = c.get(f"/api/knowledge-bases/{kb['id']}", headers=H(tok)).json()["data"]
    assert got["documents"] == 2 and got["embedder"] == "mock:512" and len(got["files"]) == 2
    hits = c.post(f"/api/knowledge-bases/{kb['id']}/search", json={"query": "laptop warranty years", "top_k": 1}, headers=H(tok)).json()["data"]
    assert len(hits) == 1 and hits[0]["filename"] == "policy.pdf" and 0 < hits[0]["score"] <= 1
    other = user(c)  # owner only
    assert c.get(f"/api/knowledge-bases/{kb['id']}", headers=H(other)).json()["error"]["code"] == "KB_NOT_FOUND"
    assert c.get("/api/knowledge-bases", headers=H(other)).json()["data"] == []
    with c.websocket_connect(f"/ws/run?token={tok}") as w:
        w.send_json({"workflow": retriever_wf(kb["id"]), "input": {"question": "when do refunds arrive"}}); evs = []
        while evs[-1:] == [] or evs[-1]["type"] not in ("run_summary", "error"): evs.append(w.receive_json())
    fin = next(x for x in evs if x["type"] == "run_finished")
    assert fin["state"]["context"][0]["filename"] == "faq.md"
    with c.websocket_connect(f"/ws/run?token={other}") as w:  # someone else's knowledge base: node error with the code
        w.send_json({"workflow": retriever_wf(kb["id"]), "input": {"question": "x"}}); evs = []
        while evs[-1:] == [] or evs[-1]["type"] not in ("run_summary", "error"): evs.append(w.receive_json())
    assert evs[-1]["type"] == "error" and evs[-1]["error"]["code"] == "KB_NOT_FOUND"
    did = got["files"][0]["id"]
    assert c.delete(f"/api/knowledge-bases/{kb['id']}/documents/{did}", headers=H(tok)).json()["success"]
    assert c.post(f"/api/knowledge-bases/{kb['id']}/reindex", headers=H(tok)).json()["data"]["chunks"] == 1
    assert c.delete(f"/api/knowledge-bases/{kb['id']}", headers=H(tok)).json()["success"]
    assert c.get(f"/api/knowledge-bases/{kb['id']}", headers=H(tok)).json()["error"]["code"] == "KB_NOT_FOUND"


def test_changing_embedder_requires_reindex(monkeypatch):
    c = TestClient(app); tok = user(c)
    kb = c.post("/api/knowledge-bases", json={"name": "K"}, headers=H(tok)).json()["data"]
    c.post(f"/api/knowledge-bases/{kb['id']}/documents", files={"file": ("a.txt", b"alpha beta")}, headers=H(tok))
    monkeypatch.setenv("OPENAI_API_KEY", "sk-env")  # the effective embedder is now OpenAI: stored mock vectors no longer match
    r = c.post(f"/api/knowledge-bases/{kb['id']}/search", json={"query": "alpha"}, headers=H(tok)).json()
    assert r["error"]["code"] == "KB_EMBEDDER_CHANGED"
