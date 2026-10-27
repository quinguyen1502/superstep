"""Subprocess wrapper for `docker` and `docker compose`. Tests pass a fake with the same methods."""
from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx


class DockerError(Exception):
    def __init__(self, message: str):
        self.message = message


class Docker:
    def docker_ok(self) -> bool:
        return _rc(["docker", "version"]) == 0

    def compose_v2(self) -> bool:
        return _rc(["docker", "compose", "version"]) == 0

    def memory_bytes(self) -> int:
        try:
            pages = os_sysconf("SC_PHYS_PAGES")
            size = os_sysconf("SC_PAGE_SIZE")
        except (ValueError, OSError):
            return 0
        if pages <= 0 or size <= 0:
            return 0
        return int(pages) * int(size)

    def disk_free_bytes(self, path: str) -> int:
        try:
            return shutil.disk_usage(path).free
        except OSError:
            return 0

    def port_owner(self, port: int) -> Optional[str]:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            try:
                sock.connect(("127.0.0.1", port))
            except OSError:
                return None
        return _listener_name(port) or "unknown"

    def load(self, tar: str) -> None:
        _check(["docker", "load", "-i", tar])

    def pull(self, image: str) -> None:
        _check(["docker", "pull", image])

    def compose(self, directory: str, project: str, args: list[str]) -> None:
        _check(_compose_argv(directory, project, args))

    def exec_bytes(self, directory: str, project: str, service: str, command: list[str]) -> bytes:
        proc = _run_bytes(_compose_argv(directory, project, ["exec", "-T", service, *command]))
        if proc.returncode != 0:
            raise DockerError(proc.stderr.decode("utf-8", "replace").strip() or "docker failed")
        return proc.stdout

    def copy_from(self, directory: str, project: str, service: str, path: str) -> bytes:
        target = _temp_path()
        try:
            _check(_compose_argv(directory, project, ["cp", f"{service}:{path}", target]))
            return Path(target).read_bytes()
        finally:
            os.unlink(target)

    def copy_to(self, directory: str, project: str, service: str, path: str, data: bytes) -> None:
        target = _temp_path()
        try:
            Path(target).write_bytes(data)
            _check(_compose_argv(directory, project, ["cp", target, f"{service}:{path}"]))
        finally:
            os.unlink(target)

    def systemd_user(self) -> bool:
        return shutil.which("systemctl") is not None

    def enable_timer(self, unit: str) -> None:
        _check(["systemctl", "--user", "daemon-reload"])
        _check(["systemctl", "--user", "enable", "--now", unit])

    def install_cron(self, marker: str, line: str) -> None:
        try:
            listed = subprocess.run(["crontab", "-l"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            current = listed.stdout if listed.returncode == 0 else ""
            start, end = f"# {marker} start", f"# {marker} end"
            kept = []
            skip = False
            for row in current.splitlines():
                if row == start:
                    skip = True
                    continue
                if row == end:
                    skip = False
                    continue
                if not skip:
                    kept.append(row)
            kept.extend([start, line, end])
            proc = subprocess.run(["crontab", "-"], input="\n".join(kept) + "\n", text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as exc:
            raise DockerError(str(exc))
        if proc.returncode != 0:
            raise DockerError(proc.stderr.strip() or "crontab failed")

    def ps(self, directory: str, project: str) -> list[dict]:
        proc = _run(["docker", "compose", "-p", project, "--project-directory", directory, "-f", f"{directory}/compose.yml", "ps", "-a", "--format", "json"])
        services = []
        for line in proc.stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(item, list):
                rows = item
            else:
                rows = [item]
            for row in rows:
                services.append({"name": row.get("Service") or row.get("Name") or "", "state": row.get("State") or row.get("Status") or ""})
        return services

    def volume_bytes(self, name: str) -> int:
        proc = _run(["docker", "system", "df", "-v"])
        for line in proc.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 3 and parts[0] == name:
                return _size_bytes(parts[-1])
        return 0

    def clock_skew_seconds(self, directory: str, project: str, service: str) -> float:
        import time
        proc = _run(["docker", "compose", "-p", project, "--project-directory", directory, "-f", f"{directory}/compose.yml", "exec", "-T", service, "date", "+%s"])
        if proc.returncode != 0 or not proc.stdout.strip():
            return 0.0
        return abs(time.time() - float(proc.stdout.strip()))

    def health(self, url: str) -> dict:
        try:
            response = httpx.get(_health_url(url), timeout=5.0)
        except httpx.HTTPError:
            return {}
        if response.status_code != 200:
            return {}
        try:
            body = response.json()
        except ValueError:
            return {}
        data = body.get("data") if isinstance(body, dict) else None
        return data if isinstance(data, dict) else {}

    def registry_version(self) -> Optional[str]:
        if not _online():
            return None
        try:
            response = httpx.get("https://github.com/quinguyen1502/superstep/releases/latest", follow_redirects=True, timeout=5.0)
        except httpx.HTTPError:
            return None
        marker = "/tag/"
        url = str(response.url)
        if marker not in url:
            return None
        tag = url.rsplit(marker, 1)[1].strip("/")
        return tag[1:] if tag.startswith("v") else tag or None

    def probe(self, url: str) -> str:
        if not _online():
            return "offline"
        try:
            httpx.get(url, timeout=3.0)
        except httpx.HTTPError:
            return "unreachable"
        return "ok"

    def wait_healthy(self, url: str, timeout: float = 60.0) -> bool:
        import time
        target = _health_url(url)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                response = httpx.get(target, timeout=2.0)
            except httpx.HTTPError:
                response = None
            if response is not None and response.status_code == 200:
                return True
            time.sleep(0.5)
        return False


def os_sysconf(name: str) -> int:
    import os
    return os.sysconf(name)


def _compose_argv(directory: str, project: str, args: list[str]) -> list[str]:
    return ["docker", "compose", "-p", project, "--project-directory", directory, "-f", f"{directory}/compose.yml", *args]


def _temp_path() -> str:
    handle = tempfile.NamedTemporaryFile(prefix="superstep-cp-", delete=False)
    handle.close()
    return handle.name


def _run(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except OSError as exc:
        raise DockerError(str(exc))


def _run_bytes(args: list[str]) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except OSError as exc:
        raise DockerError(str(exc))


def _rc(args: list[str]) -> int:
    try:
        return subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    except OSError:
        return 1


def _check(args: list[str]) -> None:
    proc = _run(args)
    if proc.returncode != 0:
        raise DockerError(proc.stderr.strip() or "docker failed")


def _online() -> bool:
    try:
        with socket.create_connection(("1.1.1.1", 443), 2):
            return True
    except OSError:
        return False


def _size_bytes(token: str) -> int:
    text = token.strip().upper()
    number = ""
    suffix = ""
    for char in text:
        if char.isdigit() or char == ".":
            number += char
        else:
            suffix += char
    if not number:
        return 0
    scale = {"": 1, "B": 1, "KB": 1000, "MB": 1000 ** 2, "GB": 1000 ** 3, "KIB": 1024, "MIB": 1024 ** 2, "GIB": 1024 ** 3}
    return int(float(number) * scale.get(suffix, 1))


def _listener_name(port: int) -> Optional[str]:
    if not shutil.which("lsof"):
        return None
    try:
        proc = subprocess.run(["lsof", "-nP", f"-iTCP:{port}", "-sTCP:LISTEN"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    except OSError:
        return None
    lines = [line for line in proc.stdout.splitlines() if line and not line.startswith("COMMAND")]
    if not lines:
        return None
    return lines[0].split(None, 1)[0]


def _health_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    if path.endswith("/api/health"):
        return url
    return url.rstrip("/") + "/api/health"
