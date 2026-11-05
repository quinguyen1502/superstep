"""Local worker transport/isolation and protected screenshot contract. Real smoke is opt-in."""
import base64
import importlib.util
import json
from pathlib import Path
import struct
import time
import uuid

import pytest

from app.api.deps import browser_artifact_service, get_db
from app.core.errors import AppError
from app.engine.browser_contract import BrowserSettings, ExecutionContext, WorkerCommand, WorkerOpen, WorkerResult
from app.engine.browser_worker import BrowserWorkerError, LocalBrowserWorker
from app.repositories.browser_artifacts import BrowserArtifactRepository
from app.repositories.user_data import UserDataRepository
from app.repositories import RunRepository
from app.models import Run
from app.services.browser_artifact_service import BrowserArtifactService
from app.services.browser_runtime_service import BrowserRuntimeService
from tests.test_chat_trigger_runs import c, api, user, H

ROOT = Path(__file__).resolve().parents[2]
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aLc0AAAAASUVORK5CYII=")


def context(principal="user-one"):
    return ExecutionContext(principal_id=principal, run_id="run-one", group_id="agent-one", connection_id="browser-one",
        configuration="a" * 64, lease_generation=1)


def test_generated_schemas_match_python_authority_contract():
    spec = importlib.util.spec_from_file_location("browser_contracts", ROOT / "scripts/browser-contracts.py")
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert json.loads((ROOT / "docker/browser-worker/contracts.json").read_text()) == module.schemas()
    assert WorkerOpen(context=context(), settings=BrowserSettings(), session_id="session-one").context == context()


def test_container_flags_and_credentials_never_in_argv(monkeypatch):
    calls = []
    worker = LocalBrowserWorker(context(), BrowserSettings(), docker="synthetic-docker")
    def docker(*argv, data=None, timeout=30):
        calls.append((argv, data))
        if argv[:3] == ("exec", worker.gateway, "python"): return "True"
        if argv[:3] == ("exec", worker.worker, "node"): return "true"
        if argv[:2] == ("exec", "-i"):
            request = json.loads(data)
            if request["method"] == "open": return '{"status":"ready"}'
        return ""
    monkeypatch.setattr(worker, "_docker", docker)
    worker.start(secrets={"proxy_username": "synthetic-user", "proxy_password": "synthetic-password", "unrelated_server_secret": "must-not-pass"})
    launches = [args for args, _ in calls if args[0] == "run"]
    browser = next(args for args in launches if "--network=none" in args)
    assert all(flag in browser for flag in ("--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--memory=768m", "--pids-limit=128", "--cpus=1"))
    assert any("dst=/egress,readonly" in item for item in browser) and not any("docker.sock" in item for item in browser)
    assert "synthetic-password" not in str(calls) and "must-not-pass" not in str(calls)
    assert "--env-file" in next(args for args in launches if worker.gateway in args)
    worker.close(); before = len(calls); worker.close(); assert len(calls) == before
    assert any(args[:2] == ("rm", "-fv") and worker.worker in args for args, _ in calls)


def test_transport_loss_never_retries_effects_and_principal_override_denied(monkeypatch):
    worker = LocalBrowserWorker(context(), BrowserSettings())
    calls = []
    def fail(*args, **kwargs): calls.append(args); raise BrowserWorkerError()
    monkeypatch.setattr(worker, "_rpc", fail)
    monkeypatch.setattr(worker, "close", lambda: None)
    command = worker.command("fill", {"observation_id": "o1", "element_id": "e1", "value": "private"}, 0)
    assert worker.call(command).status == "unknown" and len(calls) == 1
    assert worker.call(worker.command("snapshot", {}, 1)).status == "session_lost"
    foreign = command.model_copy(update={"context": context("another-principal")})
    with pytest.raises(BrowserWorkerError): worker.call(foreign)
    assert len(calls) == 2


def test_start_failure_cleans_resources_and_no_profile_downgrade(monkeypatch):
    worker = LocalBrowserWorker(context(), BrowserSettings()); cleanup = []
    monkeypatch.setattr(worker, "_docker", lambda *args, **kwargs: (_ for _ in ()).throw(BrowserWorkerError()))
    monkeypatch.setattr(worker, "close", lambda: cleanup.append(True))
    with pytest.raises(BrowserWorkerError): worker.start()
    assert cleanup == [True]
    worker = LocalBrowserWorker(context(), BrowserSettings(profile={"name": "profile", "origins": ["https://example.com"]}))
    monkeypatch.setattr(worker, "_docker", lambda *args, **kwargs: pytest.fail("unsupported profile launched a container"))
    with pytest.raises(BrowserWorkerError) as caught: worker.start()
    assert caught.value.status == "unsupported"


def test_cleanup_failure_is_visible_and_can_be_retried(monkeypatch):
    worker = LocalBrowserWorker(context(), BrowserSettings())
    monkeypatch.setattr(worker, "_docker", lambda *a, **k: (_ for _ in ()).throw(BrowserWorkerError()))
    assert worker.close() is False and worker.closed and worker.cleanup_pending
    monkeypatch.setattr(worker, "_docker", lambda *a, **k: "")
    assert worker.close() is True and not worker.cleanup_pending


def test_screenshot_owner_auth_retention_and_purge(c):
    owner, stranger = user(c), user(c)
    repo = BrowserArtifactRepository(get_db()); now = [time.time()]
    service = BrowserArtifactService(repo, clock=lambda: now[0])
    artifact_id = service.save(owner["id"], context(owner["id"]), PNG)
    assert service.read(artifact_id, owner["id"]) == PNG
    # Inject the same clock so expiration is deterministic, without sleeping.
    from app.main import app
    app.dependency_overrides[browser_artifact_service] = lambda: service
    try:
        path = f"/api/browser/artifacts/{artifact_id}"
        assert c.get(path).status_code == 401
        denied = c.get(path, headers=H(stranger["token"]))
        assert denied.status_code == 404 and denied.json()["error"]["code"] == "BROWSER_ARTIFACT_NOT_FOUND"
        own = c.get(path, headers=H(owner["token"]))
        assert own.status_code == 200 and own.content == PNG and own.headers["cache-control"] == "no-store"
        assert own.headers["content-type"] == "image/png" and "sandbox" in own.headers["content-security-policy"]
        now[0] += 3600
        assert c.get(path, headers=H(owner["token"])).status_code == 404
        assert service.sweep() == 1
        assert repo.owned(artifact_id, owner["id"], 0) is None
    finally: app.dependency_overrides.pop(browser_artifact_service, None)
    now[0] = time.time(); another = service.save(owner["id"], context(owner["id"]), PNG)
    UserDataRepository(get_db()).purge(owner["id"], runs=False)
    assert repo.owned(another, owner["id"], 0) is None


@pytest.mark.parametrize("value", [b"not an image", b"\x89PNG\r\n\x1a\n" + b"x" * (2 * 1024 * 1024),
    PNG[:16] + struct.pack(">II", 100000, 100000) + PNG[24:]])
def test_capture_bounds_reject_non_png_and_oversized_images(value):
    class Repo:
        def add(self, row): pytest.fail("invalid screenshot persisted")
    with pytest.raises(AppError) as caught: BrowserArtifactService(Repo()).save("owner", context(), value)
    assert caught.value.code == "BROWSER_ARTIFACT_INVALID"


def test_workflow_run_delete_purges_screenshot_bytes(c):
    owner = user(c); repo = BrowserArtifactRepository(get_db())
    service = BrowserArtifactService(repo)
    run_id, workflow_id = uuid.uuid4().hex, uuid.uuid4().hex
    with get_db().session() as session:
        session.add(Run(id=run_id, workflow_id=workflow_id, owner=owner["id"])); session.commit()
    artifact = service.save(owner["id"], context(owner["id"]).model_copy(update={"run_id": run_id}), PNG)
    RunRepository(get_db()).delete_for_workflow(workflow_id)
    assert repo.owned(artifact, owner["id"], 0) is None


def test_runtime_returns_persisted_capture_reference_and_refuses_missing_bytes(c):
    owner = user(c)
    worker = LocalBrowserWorker(context(owner["id"]), BrowserSettings())
    command = worker.command("screenshot", {}, 0)
    class Capture:
        def call(self, _): return WorkerResult(command_id=command.command_id, generation=1, sequence=0,
            status="confirmed", elapsed_ms=0, artifact_id="private-worker-reference")
        def artifact(self, _): return PNG
        def close(self): self.closed = True
    artifacts = browser_artifact_service()
    runtime = BrowserRuntimeService(artifacts)
    result = runtime.execute(owner["id"], Capture(), command)
    assert result.artifact_id != "private-worker-reference" and artifacts.read(result.artifact_id, owner["id"]) == PNG
    class LostCapture(Capture):
        def artifact(self, _): raise BrowserWorkerError()
    lost = LostCapture(); result = runtime.execute(owner["id"], lost, command)
    assert result.status == "session_lost" and result.artifact_id is None and lost.closed
