#!/usr/bin/env python3
"""Opt-in real isolated worker smoke, using only disposable synthetic fixture pages."""
import argparse
import json
from pathlib import Path
import struct
import subprocess
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.engine.browser_contract import BrowserSettings, ExecutionContext, WorkerArtifact
from app.engine.browser_worker import BrowserWorkerError, LocalBrowserWorker
from app.engine.sandbox.container import docker_exe


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", default=docker_exe())
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    def docker(*argv, timeout=120):
        result = subprocess.run([args.docker, *argv], cwd=ROOT, capture_output=True, text=True, timeout=timeout)
        if result.returncode: raise RuntimeError(f"Fixture Docker {argv[0]} failed: {result.stderr[-2000:]}")
        return result.stdout.strip()
    if not args.skip_build:
        docker("build", "-t", "superstep-browser-worker:1", "docker/browser-worker", timeout=600)
        docker("build", "-f", "docker/browser-gateway/Dockerfile", "-t", "superstep-browser-gateway:1", ".", timeout=120)
        docker("build", "-f", "backend/tests/fixtures/browser_egress/Gateway.Dockerfile", "-t", "superstep-browser-egress-gateway:task-0242", ".", timeout=120)
    suffix = uuid.uuid4().hex[:10]
    network, fixture = "ss-browser-smoke-net-" + suffix, "ss-browser-smoke-fixture-" + suffix
    context = ExecutionContext(principal_id="synthetic-owner", run_id="smoke-" + suffix, group_id="agent",
        connection_id="browser", configuration="a" * 64, lease_generation=1)
    worker = LocalBrowserWorker(context, BrowserSettings(allowed_origins=["http://allowed.test:8080"], max_actions=16),
        docker=args.docker, gateway_image="superstep-browser-egress-gateway:task-0242", gateway_network=network)
    production = LocalBrowserWorker(context.model_copy(update={"group_id": "production-gateway"}), BrowserSettings(), docker=args.docker)
    idle = LocalBrowserWorker(context.model_copy(update={"group_id": "idle"}), BrowserSettings(idle_timeout_s=30, lifetime_s=120),
        docker=args.docker, gateway_image="superstep-browser-egress-gateway:task-0242", gateway_network=network)
    uncertain = LocalBrowserWorker(context.model_copy(update={"group_id": "uncertain"}), BrowserSettings(action_timeout_ms=1000),
        docker=args.docker, gateway_image="superstep-browser-egress-gateway:task-0242", gateway_network=network)
    try:
        docker("network", "create", "--internal", network)
        docker("run", "-d", "--name", fixture, "--network", network, "--network-alias", "fixture", "--read-only",
            "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=64", "--memory=128m",
            "--tmpfs=/tmp:rw,nosuid,size=16m", "superstep-browser-egress-gateway:task-0242", "python", "fixture_server.py")
        worker.start()
        actual = json.loads(docker("inspect", worker.worker))[0]
        assert actual["HostConfig"]["NetworkMode"] == "none" and actual["HostConfig"]["ReadonlyRootfs"]
        assert actual["Config"]["User"] == "1001:1001" and actual["HostConfig"]["CapDrop"] == ["ALL"]
        assert actual["HostConfig"]["Memory"] == actual["HostConfig"]["MemorySwap"] == 768 * 1024 * 1024
        assert actual["HostConfig"]["PidsLimit"] == 128 and actual["HostConfig"]["NanoCpus"] == 1_000_000_000
        assert all(mount["Type"] == "volume" and not mount["RW"] for mount in actual["Mounts"])
        observed = worker.call(worker.command("navigate", {"url": "http://allowed.test:8080/form"}, 0))
        assert observed.status == "confirmed", observed.status
        assert "sensitive-prefilled-value" not in observed.model_dump_json()
        field = next(item.element_id for item in observed.observation.elements if item.role == "textbox")
        fill = worker.command("fill", {"observation_id": observed.observation.observation_id, "element_id": field, "value": "synthetic-private-value"}, 1)
        assert worker.call(fill).status == "approval_required"
        worker.approve(fill)
        altered = fill.model_copy(update={"arguments": {**fill.arguments, "value": "altered"}})
        assert worker.call(altered).status == "approval_required"  # approval applies to exact arguments only
        assert worker.call(fill).status == "confirmed"
        second = worker.call(worker.command("snapshot", {}, 2))
        assert second.status == "confirmed" and "synthetic-private-value" not in second.model_dump_json()
        button = next(item.element_id for item in second.observation.elements if item.role == "button")
        click = worker.command("click", {"observation_id": second.observation.observation_id, "element_id": button}, 3)
        assert worker.call(click).status == "approval_required"
        worker.approve(click); assert worker.call(click).status == "confirmed"
        third = worker.call(worker.command("snapshot", {}, 4))
        assert third.status == "confirmed"
        status = next(item.element_id for item in third.observation.elements if item.text == "Submitted")
        extracted = worker.call(worker.command("extract", {"observation_id": third.observation.observation_id, "fields": {"status": status}}, 5))
        assert extracted.status == "confirmed" and extracted.extracted == {"status": "Submitted"}
        captured = worker.call(worker.command("screenshot", {}, 6))
        assert captured.status == "confirmed" and captured.artifact_id and "png" not in captured.model_dump()
        png = worker.artifact(captured.artifact_id)
        assert png.startswith(b"\x89PNG\r\n\x1a\n") and struct.unpack(">II", png[16:24]) == (1024, 768)
        foreign = WorkerArtifact(context=context.model_copy(update={"principal_id": "another-owner"}), session_id=worker.session_id,
            generation=worker.generation, artifact_id=captured.artifact_id)
        try: worker._rpc("artifact", foreign)
        except BrowserWorkerError: pass
        else: raise AssertionError("Worker returned another principal's screenshot")
        stale = worker.call(worker.command("extract", {"observation_id": second.observation.observation_id, "fields": {"stale": button}}, 7))
        assert stale.status == "stale_observation"
        assert worker.call(worker.command("snapshot", {}, 99)).status == "stale_observation"
        assert worker.call(worker.command("snapshot", {}, 8)).status == "confirmed"
        for sequence in (9, 10, 11): assert worker.call(worker.command("screenshot", {}, sequence)).status == "confirmed"
        assert worker.call(worker.command("screenshot", {}, 12)).status == "failed_before_effect"  # four-image memory bound
        for sequence in (13, 14, 15): assert worker.call(worker.command("snapshot", {}, sequence)).status == "confirmed"
        assert worker.call(worker.command("snapshot", {}, 16)).status == "expired"
        try: worker.artifact(captured.artifact_id)
        except BrowserWorkerError: pass
        else: raise AssertionError("Expired worker retained an accessible screenshot")
        worker.close()
        production.start()
        assert production.call(production.command("navigate", {"url": "http://127.0.0.1:9090/private"}, 0)).status == "policy_denied"
        production.close()
        uncertain.start()
        hang = uncertain.call(uncertain.command("navigate", {"url": "http://allowed.test:8080/hang"}, 0))
        assert hang.status == "confirmed"
        target = next(item.element_id for item in hang.observation.elements if item.role == "button")
        action = uncertain.command("click", {"observation_id": hang.observation.observation_id, "element_id": target}, 1)
        uncertain.approve(action)
        assert uncertain.call(action).status == "unknown" and uncertain.closed
        idle.start(); time.sleep(31)
        assert idle.closed and not docker("ps", "-a", "--filter", f"name=ss-browser-{idle.session_id}", "--format", "{{.Names}}")
        assert idle.call(idle.command("snapshot", {}, 0)).status == "expired" and idle.closed
        remaining = docker("ps", "-a", "--filter", f"name=ss-browser-{worker.session_id}", "--format", "{{.Names}}")
        assert not remaining
        print(json.dumps({"outcome": "passed", "operations": ["navigate", "snapshot", "fill", "click", "extract", "screenshot"],
            "approval": "exact_command_only", "stale_refs": "denied", "foreign_artifact": "denied", "resource_expiry": "closed",
            "idle_expiry": "closed", "uncertain_effect_timeout": "unknown_no_retry_closed",
            "production_gateway_private_target": "denied", "screenshots_written_to_git": 0}))
    finally:
        worker.close(); production.close(); idle.close(); uncertain.close()
        subprocess.run([args.docker, "rm", "-fv", fixture], capture_output=True, timeout=30)
        subprocess.run([args.docker, "network", "rm", network], capture_output=True, timeout=30)


if __name__ == "__main__": main()
