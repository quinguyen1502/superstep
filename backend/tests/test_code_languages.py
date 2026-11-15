"""the Code-mode language registry, `data.language` and CODE_LANGUAGE_UNSUPPORTED."""
import pytest
from fastapi.testclient import TestClient
from app.core import permissions as P
from app.core.errors import AppError
from app.engine import code_languages as L, code_runtime as cr
from app.engine.python_export import to_python
from app.engine.validator import validate
from app.main import app

UPPER = 'def main(state):\n    return state["message"].upper()\n'


def wf(code, **extra):
    return {"name": "lang", "state": [{"name": "message", "type": "string"}, {"name": "out", "type": "string"}],
            "edges": [{"id": "1", "source": "s", "target": "c"}, {"id": "2", "source": "c", "target": "e"}],
            "nodes": [{"id": "s", "type": "start", "position": {"x": 0, "y": 0}, "data": {"label": "s"}},
                      {"id": "c", "type": "tool", "position": {"x": 1, "y": 0}, "data": {"label": "c", "mode": "code", "code": code, "output_field": "out", **extra}},
                      {"id": "e", "type": "end", "position": {"x": 2, "y": 0}, "data": {"label": "e"}}]}


@pytest.fixture
def on(monkeypatch):
    monkeypatch.setenv("STUDIO_ENABLE_CODE_NODES", "1"); monkeypatch.setenv("STUDIO_CODE_RUNTIME", "subprocess")


def test_nodes_without_a_language_are_python():
    assert L.language_of({"code": UPPER}) == "python" and L.language_of(None) == "python"
    assert L.get(None).id == "python" and L.LANGUAGES["python"].starter == cr.STARTER


def test_unknown_or_disabled_language_is_refused_before_running(on, monkeypatch):
    with pytest.raises(AppError) as e: cr.run_code(UPPER, {"message": "x"}, node="c", language="cobol")
    assert e.value.code == "CODE_LANGUAGE_UNSUPPORTED" and "cobol" in str(e.value.to_dict())
    monkeypatch.setenv("STUDIO_CODE_LANGUAGES", "cobol")  # only unknown ones -> not even Python
    with pytest.raises(AppError) as e: cr.run_code(UPPER, {"message": "x"})
    assert e.value.code == "CODE_LANGUAGE_UNSUPPORTED"


def test_python_still_runs_through_the_registry(on):
    assert cr.run_code(UPPER, {"message": "hi"}, language="python").value == "HI"


def test_validator_names_an_unavailable_language(on):
    errs = validate(wf(UPPER, language="cobol"))
    assert "Node c: cobol is not available on this server" in errs
    assert any(x.startswith("cobol Code nodes cannot run on this server") for x in errs)
    assert validate(wf(UPPER)) == []


def test_switching_the_language_is_writing_code():
    a, b = wf(UPPER), wf(UPPER, language="typescript")
    assert P.code_written(a, b) and not P.code_written(a, wf(UPPER, language="python"))
    assert P.code_sources(a) == {"c": UPPER}  # Python keeps the bare source, so stored graphs compare as before


def test_runtime_facts_list_each_language(on):
    c = TestClient(app)
    tok = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]
    r = c.get("/api/meta/runtime", headers={"Authorization": f"Bearer {tok}"}).json()["data"]
    assert [x["id"] for x in r["languages"]] == ["python", "typescript"] and r["languages"][0]["available"] is True  # TypeScript since
    assert r["languages"][0]["starter"] == r["starter"]  # the top level stays Python's, as before


def test_code_test_endpoint_refuses_an_unknown_language(on):
    c = TestClient(app)
    tok = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]
    r = c.post("/api/code/test", json={"source": UPPER, "state": {}, "language": "cobol"}, headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 400 and r.json()["error"]["code"] == "CODE_LANGUAGE_UNSUPPORTED"


def test_python_export_stubs_another_language():
    src = to_python(wf("export function main(state) { return 1 }", language="typescript"), "lang").code
    assert "raise NotImplementedError" in src and "typescript" in src and "export function" not in src
