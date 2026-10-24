"""Export a workflow as a runnable LangGraph project (a zip) for `langgraph dev` and LangSmith Studio.

`to_project` wraps the single file of an exporter (`python_export` / `typescript_export`) with what the LangGraph
CLI needs: `langgraph.json` naming the graph, the dependencies (`pyproject.toml` + `requirements.txt`, or
`package.json`), `.env.example` with the environment variables the code reads, and a README. The code file is the
plain export plus one line that builds the module-level `graph` the Agent Server loads; the server brings its own
checkpointer, so the graph is compiled without one. Like the exporters, the output is a pure function of its input.
"""
from __future__ import annotations
import ast, io, json, re, sys, zipfile
from typing import Dict, List
from .export_common import slug

LANGGRAPH_PY = "langgraph>=1.0"
LANGGRAPH_JS = "^1.0.0"
# The guard that runs the TypeScript example on import (Deno sets import.meta.main; Node does not, so it would run
# while the Agent Server loads the graph). In the project the example runs only through `npm run example`.
TS_MAIN = "if ((import.meta as { main?: boolean }).main !== false) await main();"
TS_MAIN_PROJECT = 'if (process.env.RUN_EXAMPLE === "1") await main();'
NPM_SPEC = re.compile(r"""(["'])npm:((?:@[\w.-]+/)?[\w.-]+)(?:@([^"']+))?\1""")
PY_ENV = re.compile(r"""os\.(?:environ\.get|getenv)\(\s*["'](\w+)["']|os\.environ\[\s*["'](\w+)["']\s*\]""")
TS_ENV = re.compile(r"""\benv\(\s*["'](\w+)["']\s*\)|process\.env\.(\w+)""")
# Keys a real model needs when LLM_PROVIDER is set, and LangSmith tracing (read by LangGraph itself).
MODEL_ENV = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GOOGLE_API_KEY"]
TRACING_ENV = ["LANGSMITH_API_KEY", "LANGSMITH_TRACING", "LANGSMITH_PROJECT"]


def _env_vars(code: str, pattern: re.Pattern) -> List[str]:
    seen: Dict[str, None] = {}
    for m in pattern.finditer(code): seen[next(g for g in m.groups() if g)] = None
    return list(seen)


def _env_example(found: List[str], uses_model: bool) -> str:
    lines = ["# Copy to .env and fill in. `langgraph dev` loads .env (see langgraph.json).", ""]
    if found: lines += ["# Read by the graph"] + [f"{k}=" for k in found] + [""]
    if uses_model:
        lines += ["# LLM nodes use an offline mock until LLM_PROVIDER is set (for example openai); then set its key"]
        lines += [f"# {k}=" for k in MODEL_ENV if k not in found] + [""]
    lines += ["# Optional: send traces to LangSmith"] + [f"# {k}=" for k in TRACING_ENV] + [""]
    return "\n".join(lines)


def _py_requirements(code: str) -> List[str]:
    """Third-party top-level imports of the file (Code nodes may add some), LangGraph first."""
    mods: Dict[str, None] = {}
    for node in ast.parse(code).body:
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else \
                [node.module] if isinstance(node, ast.ImportFrom) and node.module and not node.level else []
        for n in names:
            top = n.split(".")[0]
            if top not in sys.stdlib_module_names and top != "__future__": mods[top] = None
    mods.pop("langgraph", None)
    return [LANGGRAPH_PY] + sorted(mods)


def _readme(title: str, graph_id: str, file: str, python: bool) -> str:
    install = ['pip install -U "langgraph-cli[inmem]"', "pip install -r requirements.txt"] if python else ["npm install"]
    dev = "langgraph dev" if python else "npm run dev"
    example = f"python {file}" if python else "npm run example"
    return "\n".join([
        f"# {title}", "",
        "A LangGraph project exported from Superstep. It runs on the LangGraph Agent Server with `langgraph dev`",
        "and opens in LangSmith Studio.", "",
        "## Run", "", "```bash", *install, "cp .env.example .env", dev, "```", "",
        "The server listens on http://localhost:2024 and prints a LangSmith Studio link",
        "(https://smith.langchain.com/studio/?baseUrl=http://localhost:2024). Opening Studio needs a free LangSmith",
        "account; the local server and its API do not.", "",
        f"The graph is registered as `{graph_id}` in `langgraph.json`; it is the `graph` variable at the end of `{file}`.",
        "", "## Run the example without a server", "", "```bash", example, "```", "",
        "## Files", "",
        f"- `{file}`: the workflow as code (state, one function per node, the graph).",
        "- `langgraph.json`: the LangGraph CLI configuration.",
        "- " + ("`requirements.txt`, `pyproject.toml`" if python else "`package.json`, `tsconfig.json`") + ": dependencies.",
        "- `.env.example`: the environment variables the graph reads.", "",
        "## Notes", "",
        "- LLM nodes use an offline mock model unless `LLM_PROVIDER` is set.",
        "- Credentials, knowledge bases, MCP servers and approval channels are not exported. Retriever, MCP and Send",
        "  email nodes are stubs.",
        "- Human-in-the-loop nodes use `interrupt()`: in Studio, resume the paused thread with the answer.", ""])


def _python(code: str, title: str, graph_id: str) -> Dict[str, str]:
    file = "agent.py"
    body = code.rstrip("\n") + "\n\n\n# The graph the LangGraph Agent Server (langgraph dev, LangSmith Studio) loads, see langgraph.json.\n" \
        "# The server adds its own checkpointer, so none is given here.\ngraph = build_graph()\n"
    reqs = _py_requirements(code)
    deps = ",\n".join(f'    "{r}"' for r in reqs)
    pyproject = (f'[project]\nname = "{graph_id.replace("_", "-")}"\nversion = "0.1.0"\n'
                 f'description = "{title} (exported from Superstep)"\nrequires-python = ">=3.10"\n'
                 f"dependencies = [\n{deps},\n]\n\n[build-system]\nrequires = [\"setuptools>=61\"]\n"
                 f'build-backend = "setuptools.build_meta"\n\n[tool.setuptools]\npy-modules = ["agent"]\n')
    config = {"$schema": "https://langgra.ph/schema.json", "dependencies": ["."], "graphs": {graph_id: f"./{file}:graph"},
              "env": ".env", "python_version": "3.11"}
    return {file: body, "langgraph.json": json.dumps(config, indent=2) + "\n", "pyproject.toml": pyproject,
            "requirements.txt": "\n".join(reqs) + "\n# for a real model (LLM_PROVIDER): langchain and a provider, e.g. langchain-openai\n",
            ".env.example": _env_example(_env_vars(code, PY_ENV), "call_llm(" in code),
            "README.md": _readme(title, graph_id, file, True)}


def _typescript(code: str, title: str, graph_id: str) -> Dict[str, str]:
    file = "agent.ts"
    deps: Dict[str, str] = {"@langchain/langgraph": LANGGRAPH_JS, "@langchain/core": "^1.0.0"}
    def plain(m: re.Match) -> str:
        deps.setdefault(m.group(2), m.group(3) or "*")
        return f"{m.group(1)}{m.group(2)}{m.group(1)}"
    body = NPM_SPEC.sub(plain, code)
    body = body.replace(TS_MAIN, TS_MAIN_PROJECT).rstrip("\n") + \
        "\n\n// The graph the LangGraph Agent Server (langgraph dev, LangSmith Studio) loads, see langgraph.json.\n" \
        "// The server adds its own checkpointer, so none is given here.\nexport const graph = buildGraph();\n"
    pkg = {"name": graph_id.replace("_", "-"), "version": "0.1.0", "private": True, "type": "module",
           "description": f"{title} (exported from Superstep)",
           "scripts": {"dev": "langgraphjs dev", "example": f"RUN_EXAMPLE=1 tsx {file}"},
           "dependencies": dict(sorted(deps.items())),
           "devDependencies": {"@langchain/langgraph-cli": "^1.0.0", "tsx": "^4.19.0", "typescript": "^5.6.0"},
           "engines": {"node": ">=20"}}
    tsconfig = {"compilerOptions": {"target": "ES2022", "module": "NodeNext", "moduleResolution": "NodeNext",
                                    "strict": True, "skipLibCheck": True, "allowImportingTsExtensions": True, "noEmit": True}}
    config = {"$schema": "https://langgra.ph/schema.json", "node_version": "20", "dependencies": ["."],
              "graphs": {graph_id: f"./{file}:graph"}, "env": ".env"}
    return {file: body, "langgraph.json": json.dumps(config, indent=2) + "\n", "package.json": json.dumps(pkg, indent=2) + "\n",
            "tsconfig.json": json.dumps(tsconfig, indent=2) + "\n",
            ".env.example": _env_example(_env_vars(code, TS_ENV), "callLlm(" in code),
            "README.md": _readme(title, graph_id, file, False)}


def project_files(language: str, code: str, title: str) -> Dict[str, str]:
    """The project's files (path -> text) for an exported `code` file in `language` ("python" or "typescript")."""
    graph_id = slug(title, "workflow")
    return (_python if language == "python" else _typescript)(code, title, graph_id)


def to_project(language: str, code: str, title: str) -> bytes:
    """The project as a zip with one top-level folder; fixed timestamps keep the bytes reproducible."""
    root = slug(title, "workflow").replace("_", "-")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for path, text in sorted(project_files(language, code, title).items()):
            info = zipfile.ZipInfo(f"{root}/{path}", date_time=(1980, 1, 1, 0, 0, 0))
            info.external_attr = 0o644 << 16
            z.writestr(info, text, zipfile.ZIP_DEFLATED)
    return buf.getvalue()
