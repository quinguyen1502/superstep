"""Export a workflow as a runnable LangGraph project (zip) for `langgraph dev` and LangSmith Studio.

The project is the plain export plus `langgraph.json`, dependencies, `.env.example` and a README. The graph the
Agent Server loads is the module-level `graph`, compiled without a checkpointer (the server brings its own)."""
import importlib.util, io, json, sys, zipfile
from fastapi.testclient import TestClient
import pytest
from app.engine import project_export as P
from app.engine.examples import EXAMPLE
from app.engine.python_export import to_python
from app.engine.typescript_export import to_typescript
from app.main import app
from test_python_export import CHILD, PARENT, H, save, user

EX = {"input": {"message": "where is order A100"}, "answers": {}}


def files(language, wf=EXAMPLE, children=None, title="Customer Support"):
    write = to_python if language == "python" else to_typescript
    z = zipfile.ZipFile(io.BytesIO(P.to_project(language, write(wf, title, 3, children or {}, EX).code, title)))
    root = {n.split("/")[0] for n in z.namelist()}
    assert root == {"customer-support"} or title != "Customer Support"
    return {n.split("/", 1)[1]: z.read(n).decode() for n in z.namelist()}


def test_python_project_layout_and_config():
    f = files("python")
    assert set(f) == {"agent.py", "langgraph.json", "pyproject.toml", "requirements.txt", ".env.example", "README.md"}
    cfg = json.loads(f["langgraph.json"])
    assert cfg["graphs"] == {"customer_support": "./agent.py:graph"} and cfg["dependencies"] == ["."] and cfg["env"] == ".env"
    assert f["requirements.txt"].splitlines()[0] == P.LANGGRAPH_PY and '"langgraph>=1.0"' in f["pyproject.toml"]
    assert "LLM_PROVIDER=" in f[".env.example"] and "# LANGSMITH_API_KEY=" in f[".env.example"]
    assert "langgraph dev" in f["README.md"] and "smith.langchain.com/studio" in f["README.md"]
    assert f["agent.py"].rstrip().endswith("graph = build_graph()")


def test_python_project_graph_runs_without_a_checkpointer(tmp_path, monkeypatch):
    """The module imports (main() does not run), and `graph` runs like the canvas: the server's view of it."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    (tmp_path / "agent.py").write_text(files("python")["agent.py"])
    spec = importlib.util.spec_from_file_location("exported_agent", tmp_path / "agent.py")
    mod = importlib.util.module_from_spec(spec); sys.modules["exported_agent"] = mod
    try:
        spec.loader.exec_module(mod)
        assert mod.graph.checkpointer is None
        out = mod.graph.invoke({"message": "where is order A100"})
        assert out["intent"] == "order_status" and "A100" in out["answer"]
    finally:
        sys.modules.pop("exported_agent", None)


def test_python_project_of_the_support_agent_template_runs(tmp_path, monkeypatch):
    """TASK-0119: the Agent node template as a project: the module imports and its graph answers with the order tool."""
    from app.engine.templates import BUILTINS
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    b = next(x for x in BUILTINS if x["id"] == "builtin-support-agent")
    f = files("python", b["workflow"], title=b["name"])
    assert "langgraph" in f["requirements.txt"] and json.loads(f["langgraph.json"])["graphs"] == {"support_agent": "./agent.py:graph"}
    (tmp_path / "agent.py").write_text(f["agent.py"])
    spec = importlib.util.spec_from_file_location("exported_support_agent", tmp_path / "agent.py")
    mod = importlib.util.module_from_spec(spec); sys.modules["exported_support_agent"] = mod
    try:
        spec.loader.exec_module(mod)
        out = mod.graph.invoke({"message": "Where is my order B200?"})
        assert "In transit" in out["answer"] and [s["tool"] for s in out["steps"]] == ["lookup_order"]
    finally:
        sys.modules.pop("exported_support_agent", None)


def test_python_requirements_list_third_party_imports_only():
    assert P._py_requirements("import os, json\nimport httpx\nfrom langgraph.graph import StateGraph\nfrom . import x\n") == [P.LANGGRAPH_PY, "httpx"]


def test_typescript_project_is_node_ready():
    f = files("typescript")
    assert set(f) == {"agent.ts", "langgraph.json", "package.json", "tsconfig.json", ".env.example", "README.md"}
    assert "npm:" not in f["agent.ts"].split("*/", 1)[1], "Node cannot load Deno npm: specifiers"
    assert P.TS_MAIN not in f["agent.ts"] and P.TS_MAIN_PROJECT in f["agent.ts"], "main() must not run while the server loads the graph"
    assert f["agent.ts"].rstrip().endswith("export const graph = buildGraph();")
    pkg = json.loads(f["package.json"])
    assert pkg["type"] == "module" and pkg["scripts"]["dev"] == "langgraphjs dev"
    assert {"@langchain/langgraph", "@langchain/core", "langchain"} <= set(pkg["dependencies"])
    assert "@langchain/langgraph-cli" in pkg["devDependencies"]
    assert json.loads(f["langgraph.json"])["graphs"] == {"customer_support": "./agent.ts:graph"}


def test_npm_specifiers_of_code_nodes_become_dependencies():
    f = P.project_files("typescript", 'import { z } from "npm:zod@^3.23";\nimport x from "npm:@scope/pkg";\n' + P.TS_MAIN + "\n", "T")
    pkg = json.loads(f["package.json"])
    assert pkg["dependencies"]["zod"] == "^3.23" and pkg["dependencies"]["@scope/pkg"] == "*"
    assert 'from "zod"' in f["agent.ts"] and 'from "@scope/pkg"' in f["agent.ts"]


def test_the_zip_is_reproducible():
    code = to_python(EXAMPLE, "Customer Support", 3, {}, EX).code
    assert P.to_project("python", code, "Customer Support") == P.to_project("python", code, "Customer Support")


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client: yield client


@pytest.mark.parametrize("language,entry", [("python", "agent.py"), ("typescript", "agent.ts")])
def test_api_downloads_the_project(c, language, entry):
    u, x = user(c), user(c)
    child = save(c, u, CHILD)
    pid = save(c, u, json.loads(json.dumps(PARENT).replace('"child1"', json.dumps(child))))
    r = c.get(f"/api/workflows/{pid}/export/{language}/project", headers=H(u["token"]))
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    assert r.headers["content-disposition"].endswith(f'-{language}.zip"')
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert any(n.endswith("/" + entry) for n in names) and any(n.endswith("/langgraph.json") for n in names)
    assert c.get(f"/api/workflows/{pid}/export/{language}/project", headers=H(x["token"])).status_code == 404
    bad = c.get(f"/api/workflows/{pid}/export/cobol/project", headers=H(u["token"]))
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "EXPORT_LANGUAGE_UNSUPPORTED"
