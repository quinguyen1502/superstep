#!/usr/bin/env python3
"""Install and upgrade smoke for the all-in-one image (TASK-0156).

Uses the local image `ghcr.io/quinguyen1502/superstep:<cli version>`, or tags
`superstep:ci` to that name. No pull and no publish.

    sdk/python/.venv/bin/python scripts/cli_smoke.py

The interpreter needs `httpx` (the SDK venv, or `pip install -e sdk/python`).
`SUPERSTEP_UPGRADE_HEALTH_FAIL=1` is set only around the forced upgrade.
"""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "sdk" / "python" / "src"
if SRC.is_dir() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import superstep
from superstep.cli import run

APP = "ghcr.io/quinguyen1502/superstep"
SECRET = "sk-smoke-1234"
EMAIL = "cli-smoke@example.com"


def main() -> int:
    version = superstep.__version__
    image = f"{APP}:{version}"
    real_home = Path.home()
    home = Path(tempfile.mkdtemp(prefix="superstep-cli-smoke-"))
    os.environ["HOME"] = str(home)
    plugins = real_home / ".docker" / "cli-plugins"
    if plugins.is_dir():
        dest = home / ".docker" / "cli-plugins"
        dest.parent.mkdir(parents=True)
        dest.symlink_to(plugins)
    os.environ.pop("SUPERSTEP_UPGRADE_HEALTH_FAIL", None)
    names = []
    try:
        _ensure_image(image, version)
        tar = home / "images.tar"
        nxt = _next_version(version)
        nxt_image = f"{APP}:{nxt}"
        _check(["docker", "tag", image, nxt_image])
        _check(["docker", "save", "-o", str(tar), image, nxt_image])
        port = _free_port()
        name = f"cli-smoke-{os.getpid()}"
        directory = home / name
        fresh_dir = home / "fresh"
        url = f"http://127.0.0.1:{port}"
        names.extend([(name, directory), (name, fresh_dir)])

        _say(f"install {name} at {url}")
        code, body, err = _cli([
            "--json", "--lang", "en", "install", "--yes", "--topology", "single",
            "--name", name, "--dir", str(directory), "--url", url,
            "--admin-email", EMAIL, "--port", str(port), "--images", str(tar),
        ])
        if code != 0 or not body or not body.get("ok"):
            _die(f"install failed ({code}): {body or err}")
        password = body["admin_password"]
        _health(url)

        _say("second install refuses")
        code, body, _err = _cli([
            "--json", "--lang", "en", "install", "--yes", "--topology", "single",
            "--name", name, "--dir", str(directory), "--url", url,
            "--admin-email", EMAIL, "--port", str(_free_port()), "--images", str(tar),
        ])
        if code == 0 or not body or body.get("error", {}).get("code") != "INSTALLED":
            _die(f"second install did not refuse: {code} {body}")

        _say("store a credential")
        headers = _login(url, password)
        created = _api("POST", f"{url}/api/credentials", headers, {
            "name": "smoke", "provider": "openai", "api_key": SECRET,
        })
        cid = created["id"]
        hint = created["hint"]
        if not hint.endswith(SECRET[-4:]):
            _die(f"hint {hint!r} does not show the key")

        _say("backup")
        backups = home / "backups"
        backups.mkdir()
        code, body, err = _cli([
            "--json", "--lang", "en", "backup", "--name", name, "--dir", str(directory),
            "--to", str(backups),
        ])
        if code != 0 or not body or not body.get("ok"):
            _die(f"backup failed ({code}): {body or err}")
        archive = body["archive"]

        _say("remove the first instance so the fresh directory can take its port")
        code, body, err = _cli([
            "--json", "--lang", "en", "uninstall", "--purge", "--yes",
            "--name", name, "--dir", str(directory),
        ])
        if code != 0 or not body or not body.get("ok"):
            _die(f"uninstall failed ({code}): {body or err}")

        _say(f"install a fresh directory {fresh_dir}")
        code, body, err = _cli([
            "--json", "--lang", "en", "install", "--yes", "--topology", "single",
            "--name", name, "--dir", str(fresh_dir), "--url", url,
            "--admin-email", EMAIL, "--port", str(port), "--images", str(tar),
        ])
        if code != 0 or not body or not body.get("ok"):
            _die(f"fresh install failed ({code}): {body or err}")
        _health(url)

        _say("restore onto the fresh directory")
        code, body, err = _cli([
            "--json", "--lang", "en", "restore", archive, "--yes",
            "--name", name, "--dir", str(fresh_dir),
        ])
        if code != 0 or not body or not body.get("ok"):
            _logs(name)
            _die(f"restore failed ({code}): {body or err}")
        _health(url)
        restored = _login(url, password)
        listed = _api("GET", f"{url}/api/credentials", restored)
        match = [row for row in listed if row.get("id") == cid]
        if len(match) != 1 or match[0].get("hint") != hint:
            _die(f"credential was not restored: {listed}")
        _decrypts(url, restored, cid)

        _say(f"upgrade to {nxt} with the health-fail hook")
        os.environ["SUPERSTEP_UPGRADE_HEALTH_FAIL"] = "1"
        try:
            code, body, err = _cli([
                "--json", "--lang", "en", "upgrade", "--name", name,
                "--dir", str(fresh_dir), "--to", nxt, "--images", str(tar),
            ])
        finally:
            os.environ.pop("SUPERSTEP_UPGRADE_HEALTH_FAIL", None)
        if code == 0 or not body or body.get("error", {}).get("code") != "ROLLED_BACK":
            _die(f"upgrade did not roll back: {code} {body or err}")
        compose = (fresh_dir / "compose.yml").read_text(encoding="utf-8")
        if f"{APP}:{version}" not in compose or f"{APP}:{nxt}" in compose:
            _die(f"compose tag was not restored:\n{compose}")
        record = json.loads((fresh_dir / "instance.json").read_text(encoding="utf-8"))
        if record.get("version") != version:
            _die(f"instance version is {record.get('version')}")
        _health(url)
        again = _login(url, password)
        kept = _api("GET", f"{url}/api/credentials", again)
        if not any(row.get("id") == cid and row.get("hint") == hint for row in kept):
            _die(f"credential missing after rollback: {kept}")
        _decrypts(url, again, cid)

        _say("doctor fixture")
        _doctor(home / "doctor-fixture")
        _say("cli smoke passed")
        return 0
    finally:
        os.environ.pop("SUPERSTEP_UPGRADE_HEALTH_FAIL", None)
        seen = []
        for project, path in names:
            if (path / "compose.yml").is_file():
                subprocess.run(
                    ["docker", "compose", "-p", project, "--project-directory", str(path),
                     "-f", str(path / "compose.yml"), "down", "-v"],
                    check=False,
                )
            if project not in seen:
                seen.append(project)
        for project in seen:
            subprocess.run(["docker", "volume", "rm", "-f", f"{project}_data"], check=False)
        shutil.rmtree(home, ignore_errors=True)


def _ensure_image(image: str, version: str) -> None:
    if _image_exists(image):
        return
    local = "superstep:ci"
    if _image_exists(local):
        _check(["docker", "tag", local, image])
        _say(f"tagged {local} as {image}")
        return
    _die(
        f"missing {image}. Build the all-in-one image and tag it {image} "
        f"(or {local}) before running this smoke test. CLI version is {version}."
    )


def _image_exists(name: str) -> bool:
    proc = subprocess.run(["docker", "image", "inspect", name], capture_output=True, check=False)
    return proc.returncode == 0


def _next_version(version: str) -> str:
    parts = version.split(".")
    if not parts or not parts[-1].isdigit():
        return version + ".1"
    parts[-1] = str(int(parts[-1]) + 1)
    return ".".join(parts)


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _cli(argv: list[str]):
    import io
    from contextlib import redirect_stderr, redirect_stdout
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        code = run(argv)
    text = out.getvalue().strip()
    body = json.loads(text) if text else None
    return code, body, err.getvalue()


def _health(url: str) -> None:
    response = httpx.get(f"{url}/api/health", timeout=10.0)
    if response.status_code != 200:
        _die(f"{url}/api/health returned {response.status_code}")
    data = response.json().get("data") or {}
    if data.get("ok") is not True:
        _die(f"{url}/api/health data is {data}")


def _login(url: str, password: str) -> dict:
    response = httpx.post(
        f"{url}/api/auth/login",
        json={"email": EMAIL, "password": password},
        timeout=30.0,
    )
    body = response.json()
    token = ((body.get("data") or {}).get("token")) if response.status_code == 200 else None
    if not token:
        _die(f"login failed ({response.status_code}): {body}")
    return {"Authorization": f"Bearer {token}"}


def _api(method: str, url: str, headers: dict, payload: dict | None = None):
    response = httpx.request(method, url, headers=headers, json=payload, timeout=30.0)
    body = response.json()
    if response.status_code >= 400 or body.get("ok") is False:
        _die(f"{method} {url} failed ({response.status_code}): {body}")
    return body.get("data")


def _decrypts(url: str, headers: dict, cid: str) -> None:
    response = httpx.get(f"{url}/api/credentials/{cid}/models", headers=headers, timeout=20.0)
    try:
        body = response.json()
    except ValueError:
        body = {}
    code = (body.get("error") or {}).get("code") if isinstance(body, dict) else None
    if code == "CREDENTIAL_DECRYPT_FAILED":
        _die(f"credential {cid} did not decrypt: {body}")


def _doctor(directory: Path) -> None:
    directory.mkdir()
    (directory / "instance.json").write_text(json.dumps({
        "name": "doctor-fixture",
        "topology": "single",
        "sandbox": True,
        "version": superstep.__version__,
        "public_url": "http://127.0.0.1:9",
        "dir": str(directory),
        "remote": None,
        "created": "2026-10-28T00:00:00Z",
        "volumes": {},
    }) + "\n", encoding="utf-8")
    (directory / ".env").write_text(
        "JWT_SECRET=dev-secret-change-me\nSTUDIO_SECRET_KEY=smoke-secret\n",
        encoding="utf-8",
    )
    (directory / "compose.yml").write_text(
        "name: doctor-fixture\nservices:\n  superstep:\n    image: busybox\n",
        encoding="utf-8",
    )
    code, body, err = _cli(["--json", "--lang", "en", "doctor", "--dir", str(directory)])
    findings = (body or {}).get("findings") or []
    wanted = ("JWT_SECRET", "STUDIO_ENV", "Docker socket")
    if code == 0 or any(not any(piece in item for item in findings) for piece in wanted):
        _die(f"doctor findings {findings!r} ({code}) {err}")


def _check(argv: list[str]) -> None:
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        _die(f"{' '.join(argv)} failed: {proc.stderr.strip()}")


def _logs(project: str) -> None:
    proc = subprocess.run(
        ["docker", "logs", f"{project}-superstep-1"],
        capture_output=True, text=True, check=False,
    )
    text = (proc.stdout + proc.stderr).strip()
    if text:
        print(text[-4000:], file=sys.stderr)


def _say(message: str) -> None:
    print(message, file=sys.stderr)


def _die(message: str) -> None:
    print(message, file=sys.stderr)
    raise SystemExit(1)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except httpx.HTTPError as exc:
        _die(str(exc))
