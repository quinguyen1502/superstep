"""Import LangGraph repos: clone/unzip -> per-import venv -> inspect graphs -> workflow JSON.

SECURITY: imported code is arbitrary. With STUDIO_ENABLE_IMPORT=1 (the default runtime is
Docker) install, inspect and run happen in a container that mounts only the import directory.
STUDIO_IMPORT_RUNTIME=subprocess keeps the old host subprocess for tests. It is not a sandbox.
"""
from __future__ import annotations
import json, os, re, shutil, subprocess, sys, threading, time, uuid, zipfile
from typing import Any, Dict, List, Optional

from ..core import config
from .sandbox import container
from .sandbox.container import RUNNER_IN_CONTAINER

RUNNER = os.path.join(os.path.dirname(__file__), "sandbox", "runner.py")
INSPECT_TIMEOUT = int(os.environ.get("STUDIO_INSPECT_TIMEOUT", "120"))
RUN_TIMEOUT = int(os.environ.get("STUDIO_RUN_TIMEOUT", "300"))
INSTALL_TIMEOUT = int(os.environ.get("STUDIO_INSTALL_TIMEOUT", "900"))
GH_RE = re.compile(r"^https://github\.com/[\w.-]+/[\w.-]+?(\.git)?/?$")
JOBS: Dict[str, Dict[str, Any]] = {}
_ACTIVE = ("queued", "fetching", "installing", "inspecting")
_loaded = False
_PERSIST = ("id", "owner", "kind", "url", "branch", "subdir", "dir", "status", "log", "graphs",
            "error", "created", "required_env", "repo", "keep", "zip_path", "pid")


def root() -> str:
    return os.path.expanduser(os.environ.get("STUDIO_IMPORT_DIR") or os.path.join(config.home_dir(), "imports"))


def sub_env() -> Dict[str, str]:
    """Host environment for the subprocess runtime. The Docker runtime does not use this."""
    keep = {"PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "UV_CACHE_DIR"}
    env = {k: v for k, v in os.environ.items() if k in keep or k.endswith("_API_KEY") or k.startswith(("LANGSMITH_", "LANGCHAIN_", "OPENAI_"))}
    env.pop("JWT_SECRET", None); env["PYTHONUNBUFFERED"] = "1"; env["GIT_TERMINAL_PROMPT"] = "0"
    return env


class ImportError_(Exception):
    pass


def _log(job, msg):
    job["log"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")


def _persist(job: dict) -> None:
    path = os.path.join(job["dir"], "job.json")
    tmp = path + ".tmp"
    payload = {k: job.get(k) for k in _PERSIST}
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    os.replace(tmp, path)


def _pid_alive(pid) -> bool:
    if not pid: return False
    try: os.kill(int(pid), 0)
    except (OSError, ValueError): return False
    return True


def ensure_loaded() -> None:
    """Load job.json files. An in-progress job whose process is gone becomes an error."""
    global _loaded
    if _loaded: return
    _loaded = True
    base = root()
    if not os.path.isdir(base): return
    for name in os.listdir(base):
        path = os.path.join(base, name, "job.json")
        if not os.path.isfile(path): continue
        try: job = json.load(open(path, encoding="utf-8"))
        except (OSError, ValueError): continue
        if not isinstance(job, dict) or not job.get("id"): continue
        if job.get("status") in _ACTIVE and not _pid_alive(job.get("pid")):
            job["status"] = "error"
            job["error"] = "Import interrupted by a restart"
            try: _persist(job)
            except OSError: pass
        JOBS.setdefault(job["id"], job)


def cleanup() -> None:
    """Delete import directories that were never finalized and are older than the age limit."""
    ensure_loaded()
    age = config.import_max_age_s()
    if age <= 0: return
    base, now = root(), time.time()
    if not os.path.isdir(base): return
    for name in list(os.listdir(base)):
        directory = os.path.join(base, name)
        if not os.path.isdir(directory): continue
        job = JOBS.get(name)
        if job and job.get("keep"): continue
        if job and job.get("status") in _ACTIVE and _pid_alive(job.get("pid")): continue
        created = (job or {}).get("created") or os.path.getmtime(directory)
        if now - created > age:
            shutil.rmtree(directory, ignore_errors=True)
            JOBS.pop(name, None)


def mark_kept(jid: str) -> None:
    job = JOBS.get(jid)
    if not job: return
    job["keep"] = True
    try: _persist(job)
    except OSError: pass


def _dir_size(path: str, limit: int) -> None:
    total = 0
    for dp, dns, fns in os.walk(path):
        dns[:] = [d for d in dns if d != ".git"]
        for name in fns:
            try: total += os.path.getsize(os.path.join(dp, name))
            except OSError: continue
            if total > limit: raise ImportError_(f"Import is larger than {limit} bytes")


def _stage_runner(job_dir: str) -> str:
    dest = os.path.join(job_dir, ".runner")
    os.makedirs(dest, exist_ok=True)
    shutil.copyfile(RUNNER, os.path.join(dest, "runner.py"))
    return dest


def _docker_argv(job_dir: str, cwd: str, command: List[str], env: Dict[str, str], network: str, name: str) -> List[str]:
    return container.build(
        name=name, image=config.import_image(), job_dir=job_dir, cwd=cwd, command=command, env=env,
        network=network, memory=config.import_memory(), cpus=config.import_cpus(), pids=config.import_pids(),
        runner_dir=_stage_runner(job_dir), root=root(), host_root=config.import_host_dir(),
    )


def _host(job, cmd, cwd=None, timeout=180):
    """Fetch only. ``git clone`` does not execute repository code, and the sandbox image has no git."""
    _log(job, "$ " + " ".join(cmd))
    p = subprocess.run(cmd, cwd=cwd, env=sub_env(), capture_output=True, text=True, timeout=timeout)
    tail = (p.stdout + p.stderr).strip().splitlines()[-15:]
    for line in tail: job["log"].append("  " + line)
    if p.returncode != 0: raise ImportError_(f"Command failed ({p.returncode}): {' '.join(cmd[:3])}…")


def _sh(job, cmd, cwd=None, timeout=INSTALL_TIMEOUT):
    _log(job, "$ " + " ".join(cmd))
    if config.import_runtime() == "docker":
        name = container.container_name()
        argv = _docker_argv(job["dir"], cwd or job["dir"], cmd, container.sandbox_env(job["dir"]), "bridge", name)
        try:
            out, err, code, timed_out = container.captured(argv, name=name, timeout=timeout)
        except container.DockerMissing as exc:
            raise ImportError_(str(exc)) from None
        tail = (out + err).strip().splitlines()[-15:]
        for line in tail: job["log"].append("  " + line)
        if timed_out: raise ImportError_(f"Timeout after {timeout}s: {' '.join(cmd[:3])}…")
        if code != 0: raise ImportError_(f"Command failed ({code}): {' '.join(cmd[:3])}…")
        return
    p = subprocess.run(cmd, cwd=cwd, env=sub_env(), capture_output=True, text=True, timeout=timeout)
    tail = (p.stdout + p.stderr).strip().splitlines()[-15:]
    for line in tail: job["log"].append("  " + line)
    if p.returncode != 0: raise ImportError_(f"Command failed ({p.returncode}): {' '.join(cmd[:3])}…")


def safe_extract(zpath: str, dest: str) -> str:
    with zipfile.ZipFile(zpath) as z:
        for m in z.infolist():
            target = os.path.realpath(os.path.join(dest, m.filename))
            if not target.startswith(os.path.realpath(dest) + os.sep) and target != os.path.realpath(dest):
                raise ImportError_(f"Zip contains an unsafe path: {m.filename}")
        z.extractall(dest)
    entries = [e for e in os.listdir(dest) if not e.startswith("__MACOSX")]
    return os.path.join(dest, entries[0]) if len(entries) == 1 and os.path.isdir(os.path.join(dest, entries[0])) else dest


def find_graphs(repo: str) -> List[Dict[str, str]]:
    lj = os.path.join(repo, "langgraph.json")
    if os.path.exists(lj):
        graphs = json.load(open(lj)).get("graphs", {})
        out = []
        for gid, ref in graphs.items():
            ref = ref if isinstance(ref, str) else ref.get("path", "")
            if ":" in ref: out.append({"id": gid, "ref": ref.removeprefix("./"), "via": "langgraph.json"})
        if out: return out
    out = []
    pat = re.compile(r"^(\w+)\s*(?::[^=]+)?=\s*[^\n#]*\.compile\(", re.M)
    for dp, dns, fns in os.walk(repo):
        dns[:] = [d for d in dns if d not in (".git", ".venv", "venv", "node_modules", "tests", "test", "__pycache__")]
        for f in fns:
            if f.endswith(".py"):
                p = os.path.join(dp, f)
                try: src = open(p, encoding="utf-8", errors="ignore").read()
                except Exception: continue
                if "StateGraph" not in src: continue
                for m in pat.finditer(src):
                    rel = os.path.relpath(p, repo)
                    out.append({"id": f"{rel[:-3].replace(os.sep, '.')}.{m.group(1)}", "ref": f"{rel}:{m.group(1)}", "via": "scan"})
    return out


def runner_cmd(job_dir: str, mode: str, repo: str, ref: str):
    py = os.path.join(job_dir, "venv", "bin", "python")
    script = RUNNER_IN_CONTAINER if config.import_runtime() == "docker" else RUNNER
    return [py, script, mode, repo, ref]


def parse_lines(out: str) -> List[dict]:
    res = []
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try: res.append(json.loads(line))
            except Exception: pass
    return res


def inspect_ref(job_dir, repo, ref, secrets=None) -> dict:
    if config.import_runtime() == "docker":
        name = container.container_name()
        argv = _docker_argv(job_dir, repo, runner_cmd(job_dir, "inspect", repo, ref), container.sandbox_env(job_dir, secrets), "none", name)
        try:
            out, err, _code, timed_out = container.captured(argv, name=name, timeout=INSPECT_TIMEOUT)
        except container.DockerMissing as exc:
            raise ImportError_(str(exc)) from None
        if timed_out: raise ImportError_(f"Timeout after {INSPECT_TIMEOUT}s: inspect")
        evs = parse_lines(out)
        stderr = err
    else:
        p = subprocess.run(runner_cmd(job_dir, "inspect", repo, ref), cwd=repo, env=sub_env(), capture_output=True, text=True, timeout=INSPECT_TIMEOUT)
        evs, stderr = parse_lines(p.stdout), p.stderr
    for event in evs:
        if event.get("type") == "graph": return event
    err = next((event for event in evs if event.get("type") == "error"), None)
    raise ImportError_((err or {}).get("errors", [stderr.strip()[-800:] or "Could not inspect the graph"])[0])


def required_env(repo: str) -> List[str]:
    keys = []
    for name in (".env.example", ".env.sample", ".env.template"):
        path = os.path.join(repo, name)
        if os.path.exists(path):
            for line in open(path, errors="ignore"):
                m = re.match(r"^\s*([A-Z][A-Z0-9_]*(?:KEY|TOKEN))\s*=", line)
                if m: keys.append(m.group(1))
    return keys


def _install(job, repo: str, d: str):
    venv = os.path.join(d, "venv")
    if config.import_runtime() == "docker":
        _sh(job, ["python", "-m", "venv", venv], cwd=d, timeout=INSTALL_TIMEOUT)
        py = os.path.join(venv, "bin", "python")
        pip = [py, "-m", "pip", "install", "-q"]
    else:
        _sh(job, ["uv", "venv", "-q", venv, "--python", sys.executable] if shutil.which("uv") else [sys.executable, "-m", "venv", venv])
        py = os.path.join(venv, "bin", "python")
        pip = ["uv", "pip", "install", "-q", "--python", py] if shutil.which("uv") else [py, "-m", "pip", "install", "-q"]
    if os.path.exists(os.path.join(repo, "pyproject.toml")) or os.path.exists(os.path.join(repo, "setup.py")):
        _sh(job, pip + ["-e", repo, "langgraph", "python-dotenv"], cwd=repo)
    elif os.path.exists(os.path.join(repo, "requirements.txt")):
        _sh(job, pip + ["-r", os.path.join(repo, "requirements.txt"), "langgraph", "python-dotenv"], cwd=repo)
    else:
        _sh(job, pip + ["langgraph", "python-dotenv"], cwd=repo)


def do_import(job_id: str):
    job = JOBS[job_id]; d = job["dir"]; job["pid"] = os.getpid()
    try:
        job["status"] = "fetching"; _persist(job)
        src = os.path.join(d, "src_raw")
        if job["kind"] == "url":
            cmd = ["git", "clone", "--depth", "1"] + (["--branch", job["branch"]] if job.get("branch") else []) + [job["url"], src]
            _host(job, cmd, timeout=180)
        else:
            os.makedirs(src, exist_ok=True); src = safe_extract(job["zip_path"], src)
        repo = os.path.realpath(os.path.join(src, job.get("subdir") or ""))
        if not repo.startswith(os.path.realpath(d)) or not os.path.isdir(repo): raise ImportError_("Invalid subdir")
        _dir_size(repo, config.import_max_bytes())
        job["repo"] = repo
        job["status"] = "installing"; _persist(job)
        _install(job, repo, d)
        job["status"] = "inspecting"; _persist(job)
        refs = find_graphs(repo)
        if not refs: raise ImportError_("No graph found (langgraph.json or a compiled StateGraph variable)")
        _log(job, f"Found {len(refs)} graph(s): " + ", ".join(r["ref"] for r in refs))
        job["required_env"] = required_env(repo)
        secrets = _run_secrets({"required_env": job["required_env"]})
        graphs = []
        for ref in refs:
            try:
                graph = inspect_ref(d, repo, ref["ref"], secrets); graphs.append({**ref, "graph": graph}); _log(job, f"✓ {ref['id']}: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
            except Exception as exc:
                _log(job, f"✗ {ref['id']}: {exc}")
        if not graphs: raise ImportError_("No graph could be loaded (see log)")
        job["graphs"] = graphs
        job["status"] = "ready"; _log(job, "Done — pick a graph to create a workflow")
    except subprocess.TimeoutExpired as exc:
        job["status"] = "error"; job["error"] = f"Timeout: {exc.cmd[0] if getattr(exc, 'cmd', None) else 'command'}"; _log(job, job["error"])
    except Exception as exc:
        job["status"] = "error"; job["error"] = str(exc); _log(job, f"Error: {exc}")
    try: _persist(job)
    except OSError: pass


def start_job(owner: str, kind: str, url: str = None, branch: str = None, subdir: str = None, zip_bytes: bytes = None, sync=False) -> str:
    ensure_loaded(); cleanup()
    if kind == "url" and not GH_RE.match(url or ""): raise ImportError_("Only public GitHub URLs like https://github.com/owner/repo are supported")
    if branch and not re.match(r"^[\w./-]+$", branch): raise ImportError_("Invalid branch")
    if subdir and (".." in subdir.split("/") or subdir.startswith("/")): raise ImportError_("Invalid subdir")
    jid = uuid.uuid4().hex[:10]; d = os.path.realpath(os.path.join(root(), jid)); os.makedirs(d)
    job = {"id": jid, "owner": owner, "kind": kind, "url": url, "branch": branch, "subdir": subdir, "dir": d,
           "status": "queued", "log": [], "graphs": [], "error": None, "created": time.time(), "pid": os.getpid(), "keep": False}
    if zip_bytes is not None:
        job["zip_path"] = os.path.join(d, "upload.zip"); open(job["zip_path"], "wb").write(zip_bytes)
    JOBS[jid] = job
    _persist(job)
    if sync: do_import(jid)
    else: threading.Thread(target=do_import, args=(jid,), daemon=True).start()
    return jid


def public_job(job):
    return {k: job[k] for k in ("id", "status", "log", "error", "url", "branch", "subdir")} | {
        "graphs": [{"id": g["id"], "ref": g["ref"], "via": g["via"], "name": g["graph"].get("name"), "nodes": len(g["graph"]["nodes"]), "edges": len(g["graph"]["edges"])} for g in job["graphs"]],
        "required_env": job.get("required_env", [])}


def to_workflow(job: dict, gid: str) -> dict:
    g = next(x for x in job["graphs"] if x["id"] == gid); gr = g["graph"]
    nodes = []
    for n in gr["nodes"]:
        t = "start" if n["id"] == "__start__" else "end" if n["id"] == "__end__" else "code"
        data = {"label": "Start" if t == "start" else "End" if t == "end" else n["id"]}
        if t == "code":
            data.update({"node_name": n["id"], "ref": n.get("ref"), "source": n.get("source"), "is_llm": n.get("is_llm", False), "kind": n.get("kind"), "subgraph": n.get("subgraph", False)})
        nodes.append({"id": n["id"], "type": t, "position": {"x": 0, "y": 0}, "data": data})
    edges = []
    for i, e in enumerate(gr["edges"]):
        ed = {"id": f"e{i}", "source": e["source"], "target": e["target"], "conditional": e["conditional"]}
        if e["conditional"]: ed["label"] = e.get("label") or e["target"]
        edges.append(ed)
    name = gr.get("name") if gr.get("name") not in (None, "LangGraph") else gid
    repo_name = (job.get("url") or "upload.zip").rstrip("/").split("/")[-1].removesuffix(".git")
    return {"name": f"{repo_name}: {name}", "state": gr.get("state", []), "nodes": nodes, "edges": edges, "needs_layout": True,
            "source": {"kind": "langgraph_import", "import_id": job["id"], "graph_id": gid, "ref": g["ref"], "repo_url": job.get("url"),
                       "branch": job.get("branch"), "subdir": job.get("subdir"), "repo_dir": job["repo"], "job_dir": job["dir"],
                       "required_env": job.get("required_env", []), "imported_at": time.time()}}


def _run_secrets(source: dict) -> Dict[str, str]:
    names = list(source.get("required_env") or [])
    extra = [k.strip() for k in (os.environ.get("STUDIO_IMPORT_SECRETS") or "").split(",") if k.strip()]
    out = {}
    for key in names + extra:
        if key in os.environ and container.allow_secret(key): out[key] = os.environ[key]
    return out


def _open_run(job_dir: str, repo: str, ref: str, secrets: Dict[str, str]) -> container.Child:
    cmd = runner_cmd(job_dir, "run", repo, ref)
    if config.import_runtime() == "docker":
        name = container.container_name()
        argv = _docker_argv(job_dir, repo, cmd, container.sandbox_env(job_dir, secrets), config.import_network(), name)
        return container.start(argv, name=name)
    return container.local_child(cmd, cwd=repo, env=sub_env())


def run_imported(wf: dict, inp: dict, on_proc=None, resume: dict | None = None, checkpointing: bool = False):
    """Sync generator: run the original compiled graph and yield events.

    Docker is the runtime when import is enabled. The subprocess runtime remains for tests.
    checkpointing: the runner attaches an in-memory LangGraph saver (when the graph has none) and yields
    ``_checkpoint`` {node, nodes, blob} after each superstep; resume = {"blob"} continues it.
    """
    s = wf["source"]
    inp = {**inp, **({"__checkpointing__": True} if checkpointing else {}), **({"__resume__": resume["blob"]} if resume and resume.get("blob") else {})}
    missing = [k for k in s.get("required_env", []) if k not in os.environ and not _in_dotenv(s["repo_dir"], k)]
    # A Docker venv symlinks this file at the image interpreter. On the host that target
    # does not exist, so exists() would look like a deleted venv. lexists() checks the link.
    if not os.path.lexists(os.path.join(s["job_dir"], "venv", "bin", "python")):
        yield {"type": "error", "errors": ["The import environment is gone (venv deleted). Please import the repo again."]}; return
    try:
        child = _open_run(s["job_dir"], s["repo_dir"], s["ref"], _run_secrets(s))
    except container.DockerMissing as exc:
        yield {"type": "error", "errors": [str(exc)]}; return
    if on_proc: on_proc(child)
    timed_out = False

    def _kill():
        nonlocal timed_out
        timed_out = True
        child.kill()

    timer = threading.Timer(RUN_TIMEOUT, _kill); timer.start()
    child._p.stdin.write(json.dumps(inp)); child._p.stdin.close()
    got_end = False
    try:
        for line in child.stdout:
            line = line.strip()
            if not line.startswith("{"): continue
            try: ev = json.loads(line)
            except Exception: continue
            if ev.get("type") == "error" and missing:
                ev["errors"] = ev.get("errors", []) + [f"The repo requires variables: {', '.join(missing)} (not set in the server env or the repo .env)"]
            ev.pop("trace", None)
            if ev.get("node"): ev.setdefault("label", {"__start__": "Start", "__end__": "End"}.get(ev["node"], ev["node"]))
            if ev.get("type") in ("run_finished", "error"): got_end = True
            yield ev
        child.wait()
    finally:
        timer.cancel()
        if child._p.poll() is None: child.kill()
    if not got_end:
        killed = container.failure_event(child.returncode, timed_out, RUN_TIMEOUT, child.stderr_text())
        if killed: yield killed
        else:
            err = child.stderr_text()[-800:]
            yield {"type": "error", "errors": [f"Subprocess exited abnormally (code {child.returncode}, possibly a {RUN_TIMEOUT}s timeout). {err}"]}


def _in_dotenv(repo, key):
    p = os.path.join(repo, ".env")
    return os.path.exists(p) and any(l.strip().startswith(key + "=") and l.strip() != key + "=" for l in open(p, errors="ignore"))
