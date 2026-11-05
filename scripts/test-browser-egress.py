#!/usr/bin/env python3
"""Opt-in disposable Docker/Chromium egress proof. Never runs against real websites/accounts."""
import argparse
import json
from pathlib import Path
import shutil
import subprocess
import time
import uuid

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "backend/tests/fixtures/browser_egress"
GATEWAY_IMAGE = "superstep-browser-egress-gateway:task-0242"
BROWSER_IMAGE = "superstep-browser-egress-browser:task-0242"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docker", default=shutil.which("docker"))
    parser.add_argument("--skip-build", action="store_true")
    args = parser.parse_args()
    if not args.docker: parser.error("Docker CLI is required; supply --docker when it is outside PATH")

    def docker(*argv, timeout=120):
        result = subprocess.run([args.docker, *argv], cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        if result.returncode: raise RuntimeError(f"Docker {argv[0]} failed: {result.stderr[-4000:]} {result.stdout[-4000:]}")
        return result.stdout.strip()

    if not args.skip_build:
        for name, image in (("Gateway", GATEWAY_IMAGE), ("Browser", BROWSER_IMAGE)):
            docker("build", "-f", str(FIXTURE / f"{name}.Dockerfile"), "-t", image, ".", timeout=600)
    prefix = "ss-browser-egress-" + uuid.uuid4().hex[:10]
    network, fixture, containers, volumes = prefix + "-net", prefix + "-fixture", [], []
    results = []
    try:
        docker("network", "create", "--internal", network)
        containers.append(fixture)
        docker("run", "-d", "--name", fixture, "--network", network, "--network-alias", "fixture",
            "--read-only", "--cap-drop=ALL", "--security-opt=no-new-privileges", "--pids-limit=64", "--memory=128m",
            "--tmpfs=/tmp:rw,nosuid,size=16m", GATEWAY_IMAGE, "python", "fixture_server.py")
        settings = json.loads(docker("inspect", fixture))[0]
        fixture_ip = settings["NetworkSettings"]["Networks"][network]["IPAddress"]
        for mode in ("direct", "custom", "operator_default"):
            volume, gateway, browser = f"{prefix}-{mode}-socket", f"{prefix}-{mode}-gateway", f"{prefix}-{mode}-browser"
            volumes.append(volume); containers.extend([gateway, browser])
            docker("volume", "create", volume)
            docker("run", "-d", "--name", gateway, "--network", network, "--read-only", "--cap-drop=ALL",
                "--security-opt=no-new-privileges", "--pids-limit=64", "--memory=128m", "--cpus=1",
                "--tmpfs=/tmp:rw,nosuid,size=16m", "--env", f"FIXTURE_ROUTE={mode}",
                "--mount", f"type=volume,src={volume},dst=/egress", GATEWAY_IMAGE)
            for _ in range(40):
                try:
                    ready = docker("exec", gateway, "python", "-c", "import os;print(os.path.exists('/egress/gateway.sock'))")
                    if ready == "True": break
                except RuntimeError: pass
                time.sleep(0.1)
            else: raise RuntimeError("Gateway socket unavailable: " + docker("logs", gateway))
            docker("create", "--name", browser, "--network=none", "--init", "--read-only", "--cap-drop=ALL",
                "--security-opt=no-new-privileges", "--security-opt", f"seccomp={ROOT / 'backend/app/engine/browser_seccomp.json'}",
                "--pids-limit=128", "--memory=768m", "--cpus=1", "--shm-size=256m", "--env", "HOME=/tmp",
                "--env", f"FIXTURE_IP={fixture_ip}", "--env", f"FIXTURE_ROUTE={mode}",
                "--tmpfs=/tmp:rw,nosuid,size=256m", "--mount", f"type=volume,src={volume},dst=/egress,readonly", BROWSER_IMAGE)
            actual = json.loads(docker("inspect", browser))[0]
            assert actual["HostConfig"]["NetworkMode"] == "none" and actual["HostConfig"]["ReadonlyRootfs"]
            assert actual["Config"]["User"] == "pwuser" and actual["HostConfig"]["CapDrop"] == ["ALL"]
            assert all(mount["Type"] == "volume" and not mount["RW"] for mount in actual["Mounts"])
            try: output = docker("start", "-a", browser, timeout=120)
            except RuntimeError as error:
                diagnostics = docker("exec", gateway, "python", "-c", "import os;print(os.stat('/egress/gateway.sock'));print(open('/tmp/gateway-stats.json').read() if os.path.exists('/tmp/gateway-stats.json') else 'no gateway traffic')")
                raise RuntimeError(str(error) + "\nGateway: " + diagnostics) from None
            state = json.loads(docker("inspect", browser))[0]["State"]
            if state["ExitCode"] != 0: raise RuntimeError("Browser fixture failed: " + docker("logs", browser))
            browser_result = json.loads(output.splitlines()[-1])
            audit = json.loads(docker("exec", gateway, "cat", "/tmp/gateway-stats.json"))
            assert sum(event["event"] == "denied" for event in audit["events"]) >= 5
            assert "synthetic-query-secret" not in json.dumps(audit)
            if mode != "direct": assert audit["dns"]["fixture-proxy"] == 1  # pinned for every later command
            results.append({"route": mode, "browser": browser_result, "gateway": audit})
            print(json.dumps({"route": mode, "outcome": "passed", "denied": sum(e["event"] == "denied" for e in audit["events"])}), flush=True)
        stats = json.loads(docker("exec", fixture, "cat", "/tmp/fixture-stats.json"))
        assert not any(item["leaked_proxy_auth"] for item in stats["requests"])
        assert stats["connects"] and all(item["address"] == fixture_ip for item in stats["connects"])
        assert not any(item["path"] in {"/private", "/image", "/secret", "/metadata", "/second", "/no-fallback", "/no-proxy", "/sw.js", "/service-worker"} for item in stats["requests"])
        print(json.dumps({"outcome": "passed", "routes": len(results), "numeric_proxy_connects": len(stats["connects"])}), flush=True)
    finally:
        for container in reversed(containers):
            subprocess.run([args.docker, "rm", "-fv", container], capture_output=True, timeout=30)
        for volume in volumes:
            subprocess.run([args.docker, "volume", "rm", volume], capture_output=True, timeout=30)
        subprocess.run([args.docker, "network", "rm", network], capture_output=True, timeout=30)


if __name__ == "__main__": main()
