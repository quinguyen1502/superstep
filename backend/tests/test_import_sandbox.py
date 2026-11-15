"""the import flag, the Docker argv, and job persistence. No daemon required."""
import json, os, time

from fastapi.testclient import TestClient

from app.core import config
from app.engine import repo_import as importer
from app.engine.sandbox import container
from app.main import app


def test_runtime_follows_the_flag(monkeypatch):
    monkeypatch.delenv("STUDIO_IMPORT_RUNTIME", raising=False)
    monkeypatch.delenv("STUDIO_ENABLE_IMPORT", raising=False)
    assert config.import_enabled() is False
    assert config.import_runtime() == "subprocess"
    monkeypatch.setenv("STUDIO_ENABLE_IMPORT", "1")
    assert config.import_runtime() == "docker"
    monkeypatch.setenv("STUDIO_IMPORT_RUNTIME", "subprocess")
    assert config.import_runtime() == "subprocess"
    monkeypatch.setenv("STUDIO_IMPORT_NETWORK", "host")
    assert config.import_network() == "bridge"


def test_disabled_import_is_404_after_auth(monkeypatch):
    monkeypatch.delenv("STUDIO_ENABLE_IMPORT", raising=False)
    c = TestClient(app)
    assert c.post("/api/import", data={"url": "https://github.com/langchain-ai/new-langgraph-project"}).status_code == 401
    tok = c.post("/api/auth/login", json={"email": "admin@example.com", "password": "admin123"}).json()["data"]["token"]
    H = {"Authorization": f"Bearer {tok}"}
    posted = c.post("/api/import", data={"url": "https://github.com/langchain-ai/new-langgraph-project"}, headers=H)
    assert posted.status_code == 404 and posted.json()["error"]["code"] == "IMPORT_DISABLED"
    got = c.get("/api/import/missing", headers=H)
    assert got.status_code == 404 and got.json()["error"]["code"] == "IMPORT_DISABLED"
    done = c.post("/api/import/missing/finalize", json={"graph_id": "agent"}, headers=H)
    assert done.status_code == 404 and done.json()["error"]["code"] == "IMPORT_DISABLED"


def test_health_reports_the_flag(monkeypatch):
    c = TestClient(app)
    monkeypatch.delenv("STUDIO_ENABLE_IMPORT", raising=False)
    assert c.get("/api/health").json()["data"]["import_enabled"] is False
    monkeypatch.setenv("STUDIO_ENABLE_IMPORT", "1")
    assert c.get("/api/health").json()["data"]["import_enabled"] is True


def test_docker_desktop_cli_when_path_has_no_docker(monkeypatch):
    monkeypatch.setattr(container.shutil, "which", lambda name: None)
    monkeypatch.setattr(container.os.path, "isfile", lambda path: path == container._MAC_DOCKER)
    monkeypatch.setattr(container.os, "access", lambda path, mode: path == container._MAC_DOCKER)
    assert container.docker_exe() == container._MAC_DOCKER
    monkeypatch.setattr(container.shutil, "which", lambda name: "/usr/local/bin/docker")
    assert container.docker_exe() == "/usr/local/bin/docker"
    monkeypatch.setattr(container.shutil, "which", lambda name: None)
    monkeypatch.setattr(container.os.path, "isfile", lambda path: False)
    assert container.docker_exe() == "docker"


def test_sandbox_env_drops_server_secrets():
    env = container.sandbox_env("/imports/job", {
        "OPENAI_API_KEY": "sk-test", "JWT_SECRET": "nope", "STUDIO_DB": "nope",
        "DATABASE_URL": "postgres://x", "EVIL": "a\nb", "ok_key": "nope",
    })
    assert env["OPENAI_API_KEY"] == "sk-test" and env["HOME"] == "/imports/job"
    assert "JWT_SECRET" not in env and "STUDIO_DB" not in env and "DATABASE_URL" not in env
    assert "EVIL" not in env and "ok_key" not in env
    assert container.allow_secret("STUDIO_SECRET_KEY") is False
    assert container.allow_secret("REDIS_URL") is False


def test_docker_argv_mounts_only_the_job(tmp_path):
    job = tmp_path / "job"
    runner = job / ".runner"
    runner.mkdir(parents=True)
    (runner / "runner.py").write_text("print(1)\n")
    env = container.sandbox_env(str(job), {"OPENAI_API_KEY": "sk-test", "JWT_SECRET": "nope"})
    argv = container.build(
        name="lgsabc", image="python:3.12-slim", job_dir=str(job), cwd=str(job),
        command=["python", "-c", "print(1)"], env=env, network="none",
        memory="1g", cpus="1", pids=256, runner_dir=str(runner),
        root=str(tmp_path), host_root="/host/imports",
    )
    assert argv[argv.index("--network") + 1] == "none"
    assert argv[argv.index("--memory") + 1] == "1g"
    assert argv[argv.index("--memory-swap") + 1] == "1g"
    assert argv[argv.index("--cpus") + 1] == "1"
    assert argv[argv.index("--pids-limit") + 1] == "256"
    assert "--read-only" in argv and argv[argv.index("--cap-drop") + 1] == "ALL"
    assert "no-new-privileges:true" in argv
    mounts = [argv[i + 1] for i, arg in enumerate(argv) if arg == "-v"]
    assert len(mounts) == 2
    assert mounts[0].startswith("/host/imports/job:") and mounts[0].endswith(":rw")
    assert mounts[1].startswith("/host/imports/job/.runner:") and mounts[1].endswith(":/opt/studio-runner:ro")
    assert argv[argv.index("--env-file") + 1] == "/host/imports/job/.sandbox.env"
    blob = " ".join(argv)
    assert "sk-test" not in blob and "JWT_SECRET" not in blob
    written = (job / ".sandbox.env").read_text()
    assert "OPENAI_API_KEY=sk-test" in written and "JWT_SECRET" not in written
    assert os.stat(job / ".sandbox.env").st_mode & 0o777 == 0o600
    outside = container.host_path("/etc/passwd", str(tmp_path), "/host/imports")
    assert outside == os.path.realpath("/etc/passwd")


def test_inspect_network_is_none_and_install_network_is_bridge(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_IMPORT_RUNTIME", "docker")
    seen = []
    monkeypatch.setattr(importer.container, "build", lambda **kw: seen.append(kw) or ["docker", "run"])
    monkeypatch.setattr(importer.container, "captured", lambda *a, **k: ('{"type":"graph","nodes":[],"edges":[]}\n', "", 0, False))
    importer.inspect_ref(str(tmp_path), str(tmp_path), "a.py:g", {"OPENAI_API_KEY": "sk-test"})
    importer._sh({"dir": str(tmp_path), "log": []}, ["python", "-m", "venv", "venv"])
    assert seen[0]["network"] == "none" and seen[0]["env"]["OPENAI_API_KEY"] == "sk-test"
    assert "JWT_SECRET" not in seen[0]["env"]
    assert seen[1]["network"] == "bridge"


def test_git_clone_stays_on_the_host(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_IMPORT_DIR", str(tmp_path))
    monkeypatch.setenv("STUDIO_IMPORT_RUNTIME", "docker")
    monkeypatch.setenv("STUDIO_ENABLE_IMPORT", "1")
    monkeypatch.setattr(importer, "_loaded", False)
    calls = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        class P:
            returncode = 0
            stdout = ""
            stderr = ""
        return P()

    def no_sandbox(*args, **kwargs):
        raise AssertionError("sandbox")

    monkeypatch.setattr(importer.subprocess, "run", fake_run)
    monkeypatch.setattr(importer.container, "captured", no_sandbox)
    jid = importer.start_job("u", "url", url="https://github.com/langchain-ai/new-langgraph-project", sync=True)
    try:
        assert calls and calls[0][:2] == ["git", "clone"]
        assert importer.JOBS[jid]["status"] == "error"
        assert "sandbox" not in (importer.JOBS[jid]["error"] or "")
    finally:
        importer.JOBS.pop(jid, None)


def test_docker_venv_symlink_is_not_a_deleted_environment(tmp_path, monkeypatch):
    """The image interpreter is not on the host, so the venv python is a broken symlink."""
    py = tmp_path / "venv" / "bin" / "python"
    py.parent.mkdir(parents=True)
    py.symlink_to("/usr/local/bin/python")
    assert os.path.lexists(py) and not os.path.exists(py)

    def opened(*args, **kwargs):
        raise RuntimeError("opened")

    monkeypatch.setattr(importer, "_open_run", opened)
    wf = {"source": {"job_dir": str(tmp_path), "repo_dir": str(tmp_path), "ref": "g.py:g", "required_env": []}}
    try:
        list(importer.run_imported(wf, {}))
    except RuntimeError as exc:
        assert str(exc) == "opened"
    else:
        raise AssertionError("venv symlink was treated as missing")


def test_limits_become_an_error_event():
    timed = container.failure_event(1, True, 30, "slow")
    oom = container.failure_event(137, False, 30, "killed")
    assert timed["type"] == "error" and "time limit (30s)" in timed["errors"][0]
    assert oom["type"] == "error" and "memory limit" in oom["errors"][0]
    assert container.failure_event(1, False, 30, "bug") is None


def test_dir_size_cap_skips_git(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_IMPORT_MAX_BYTES", "8")
    git = tmp_path / ".git"
    git.mkdir()
    (git / "objects").write_bytes(b"x" * 100)
    (tmp_path / "ok.txt").write_bytes(b"hi")
    importer._dir_size(str(tmp_path), config.import_max_bytes())
    (tmp_path / "big.txt").write_bytes(b"0123456789")
    try:
        importer._dir_size(str(tmp_path), config.import_max_bytes())
        raise AssertionError("expected the size cap")
    except importer.ImportError_ as exc:
        assert "larger than" in str(exc)


def test_jobs_reload_and_cleanup(tmp_path, monkeypatch):
    monkeypatch.setenv("STUDIO_IMPORT_DIR", str(tmp_path))
    monkeypatch.setenv("STUDIO_IMPORT_MAX_AGE_HOURS", "1")
    monkeypatch.setattr(importer, "_loaded", False)
    monkeypatch.setattr(importer, "_pid_alive", lambda pid: False)
    ids = ("oldjob", "keptjob", "freshjob")

    def write(jid, **extra):
        directory = tmp_path / jid
        directory.mkdir()
        payload = {"id": jid, "owner": "u", "status": "queued", "pid": 1, "created": time.time() - 10 * 3600,
                   "dir": str(directory), "keep": False, "log": [], "graphs": [], "error": None}
        payload.update(extra)
        (directory / "job.json").write_text(json.dumps(payload))

    write("oldjob")
    write("keptjob", keep=True, status="ready")
    write("freshjob", created=time.time(), status="ready")
    try:
        importer.ensure_loaded()
        assert importer.JOBS["oldjob"]["error"] == "Import interrupted by a restart"
        importer.mark_kept("keptjob")
        assert json.loads((tmp_path / "keptjob" / "job.json").read_text())["keep"] is True
        importer.cleanup()
        assert not (tmp_path / "oldjob").exists()
        assert (tmp_path / "keptjob").exists() and (tmp_path / "freshjob").exists()
    finally:
        for jid in ids:
            importer.JOBS.pop(jid, None)
