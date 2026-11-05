"""Local isolated browser supervisor. Docker stdin/exec transports private JSON, never model authority.

No application endpoint calls this until run binding/approvals are integrated.
The trusted service selects images/network and the effective principal/context.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import uuid

from .browser_contract import (BrowserSettings, ExecutionContext, WorkerCommand, WorkerControl,
                               WorkerOpen, WorkerArtifact, WorkerResult)
from .sandbox.container import docker_exe
from pydantic import ValidationError


class BrowserWorkerError(Exception):
    def __init__(self, status="session_lost"):
        self.status = status
        super().__init__("Browser worker " + status)


class LocalBrowserWorker:
    def __init__(self, context: ExecutionContext, settings: BrowserSettings, *, docker=None,
                 image="superstep-browser-worker:1", gateway_image="superstep-browser-gateway:1",
                 gateway_network="bridge", seccomp=None):
        self.context, self.settings = context, settings
        self.docker, self.image, self.gateway_image, self.gateway_network = docker or docker_exe(), image, gateway_image, gateway_network
        self.seccomp = str(seccomp or Path(__file__).with_name("browser_seccomp.json"))
        self.session_id, self.generation = uuid.uuid4().hex, 1
        self.worker, self.gateway, self.volume = (f"ss-browser-{self.session_id}-{part}" for part in ("worker", "gateway", "socket"))
        self.started, self.closed = False, False
        self.cleanup_pending = False
        self._idle_timer = self._lifetime_timer = None
        self._last_activity = time.monotonic()

    def _arm_idle(self):
        if self.closed or not self.started: return
        if self._idle_timer is not None: self._idle_timer.cancel()
        remaining = max(0.001, self.settings.idle_timeout_s - (time.monotonic() - self._last_activity))
        self._idle_timer = threading.Timer(remaining, self.close); self._idle_timer.daemon = True; self._idle_timer.start()

    def _docker(self, *args, data=None, timeout=30):
        try:
            result = subprocess.run([self.docker, *args], input=data, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
            if result.returncode:
                cleanup = args[:1] == ("rm",) or args[:2] == ("volume", "rm")
                if cleanup and any(marker in result.stderr.lower() for marker in (b"no such container", b"no such volume")):
                    raise BrowserWorkerError("missing")
                raise BrowserWorkerError()
            if len(result.stdout) > 4 * 1024 * 1024: raise BrowserWorkerError()
            return result.stdout.decode("utf-8")
        except (OSError, subprocess.TimeoutExpired, UnicodeError): raise BrowserWorkerError() from None

    def _rpc(self, method, value, timeout=65):
        if self.closed: raise BrowserWorkerError("expired")
        payload = json.dumps({"method": method, "body": value.model_dump()}, ensure_ascii=False, allow_nan=False).encode()
        if len(payload) > 256 * 1024: raise BrowserWorkerError("failed_before_effect")
        try:
            result = json.loads(self._docker("exec", "-i", self.worker, "node", "/opt/browser-worker/rpc.cjs", data=payload, timeout=timeout))
            if not isinstance(result, dict): raise BrowserWorkerError()
            return result
        except (ValueError, TypeError): raise BrowserWorkerError() from None

    def start(self, *, secrets=None, approved_proxies=(), operator_default=None):
        if self.started or self.closed: raise BrowserWorkerError("failed_before_effect")
        if self.settings.provider != "local" or self.settings.profile: raise BrowserWorkerError("unsupported")
        configuration = {"allowed_origins": self.settings.allowed_origins, "proxy": self.settings.proxy.model_dump(),
            "secrets": {key: value for key, value in (secrets or {}).items() if key in {"proxy_username", "proxy_password"}},
            "approved_proxies": list(approved_proxies), "operator_default": operator_default, "lifetime_s": self.settings.lifetime_s}
        try:
            self._docker("volume", "create", self.volume)
            # --env-file is read by the local Docker client; only its private filename enters argv.
            # Nothing is mounted from the host into either untrusted browser or gateway.
            with tempfile.NamedTemporaryFile(mode="w+", prefix="ss-browser-config-", encoding="utf-8") as secret_file:
                secret_file.write("STUDIO_BROWSER_GATEWAY_CONFIG=" + json.dumps(configuration, ensure_ascii=True, allow_nan=False) + "\n")
                secret_file.flush()
                self._docker("run", "-d", "--name", self.gateway, "--network", self.gateway_network,
                    "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=64", "--memory=128m", "--memory-swap=128m", "--cpus=1",
                    "--tmpfs=/tmp:rw,nosuid,size=16m", "--env-file", secret_file.name,
                    "--mount", f"type=volume,src={self.volume},dst=/egress", self.gateway_image)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                ready = self._docker("exec", self.gateway, "python", "-c", "import os;print(os.path.exists('/egress/gateway.sock'))")
                if ready.strip() == "True": break
                time.sleep(0.1)
            else: raise BrowserWorkerError("failed_before_effect")
            self._docker("run", "-d", "--name", self.worker, "--network=none", "--init", "--read-only",
                "--cap-drop=ALL", "--security-opt=no-new-privileges", "--security-opt", f"seccomp={self.seccomp}",
                "--pids-limit=128", "--memory=768m", "--memory-swap=768m", "--cpus=1", "--shm-size=256m",
                "--env", "HOME=/tmp", "--tmpfs=/tmp:rw,nosuid,size=256m",
                "--mount", f"type=volume,src={self.volume},dst=/egress,readonly", self.image)
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                ready = self._docker("exec", self.worker, "node", "-e", "console.log(require('fs').existsSync('/tmp/browser-control.sock'))")
                if ready.strip() == "true": break
                time.sleep(0.1)
            else: raise BrowserWorkerError("failed_before_effect")
            opened = WorkerOpen(context=self.context, settings=self.settings, session_id=self.session_id, generation=self.generation)
            if self._rpc("open", opened).get("status") != "ready": raise BrowserWorkerError("failed_before_effect")
            self.started = True
            self._last_activity = time.monotonic(); self._arm_idle()
            self._lifetime_timer = threading.Timer(self.settings.lifetime_s, self.close)
            self._lifetime_timer.daemon = True; self._lifetime_timer.start()
            return self
        except BaseException:
            self.close()
            raise

    def command(self, operation, arguments, sequence, command_id=None):
        return WorkerCommand(context=self.context, session_id=self.session_id, generation=self.generation,
            sequence=sequence, command_id=command_id or uuid.uuid4().hex, operation=operation,
            arguments=arguments, timeout_ms=self.settings.action_timeout_ms)

    def call(self, command: WorkerCommand):
        if command.context != self.context or command.session_id != self.session_id or command.generation != self.generation:
            raise BrowserWorkerError("policy_denied")
        if self._idle_timer is not None: self._idle_timer.cancel()
        try:
            result = WorkerResult.model_validate(self._rpc("command", command, timeout=command.timeout_ms / 1000 + 5))
            if (result.command_id, result.generation, result.sequence) != (command.command_id, self.generation, command.sequence):
                raise BrowserWorkerError()
            if result.status in {"expired", "session_lost", "unknown", "cancelled"}: self.close()
            elif result.status not in {"approval_required", "stale_observation"}: self._last_activity = time.monotonic()
            return result
        except (BrowserWorkerError, ValidationError, ValueError, TypeError) as error:
            # Lost transport cannot establish whether a click/fill happened. Never retry here.
            status = "expired" if isinstance(error, BrowserWorkerError) and error.status == "expired" else "unknown" if command.operation in {"click", "fill"} else "session_lost"
            self.close()
            return WorkerResult(command_id=command.command_id, generation=self.generation, sequence=command.sequence, status=status, elapsed_ms=0)
        finally: self._arm_idle()

    def approve(self, command: WorkerCommand):
        """Trusted control port only; run/approval service must verify durable human approval before invoking."""
        if command.context != self.context or command.session_id != self.session_id: raise BrowserWorkerError("policy_denied")
        return self._rpc("approve", command)

    def artifact(self, artifact_id):
        request = WorkerArtifact(context=self.context, session_id=self.session_id, generation=self.generation, artifact_id=artifact_id)
        result = self._rpc("artifact", request)
        try: value = base64.b64decode(result["png"], validate=True)
        except (ValueError, KeyError, TypeError): raise BrowserWorkerError() from None
        if result.get("artifact_id") != artifact_id or not value.startswith(b"\x89PNG\r\n\x1a\n") or len(value) > 2 * 1024 * 1024:
            raise BrowserWorkerError()
        return value

    def close(self):
        if self.closed and not self.cleanup_pending: return True
        self.closed = True
        self.cleanup_pending = False
        for timer in (self._idle_timer, self._lifetime_timer):
            if timer is not None: timer.cancel()
        # Every name is generated locally; cleanup never addresses user-provided Docker objects.
        for args in (("rm", "-fv", self.worker), ("rm", "-fv", self.gateway), ("volume", "rm", self.volume)):
            try: self._docker(*args, timeout=15)
            except BrowserWorkerError as error:
                if error.status != "missing": self.cleanup_pending = True
        return not self.cleanup_pending

    def __enter__(self): return self.start()
    def __exit__(self, *_): self.close()
