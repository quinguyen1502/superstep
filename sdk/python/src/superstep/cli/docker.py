"""Subprocess wrapper for `docker` and `docker compose`. Tests pass a fake with the same methods."""
from __future__ import annotations

import shutil
import socket
import subprocess
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
        _check(["docker", "compose", "-p", project, "--project-directory", directory, "-f", f"{directory}/compose.yml", *args])

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


def _rc(args: list[str]) -> int:
    try:
        return subprocess.run(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    except OSError:
        return 1


def _check(args: list[str]) -> None:
    try:
        proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except OSError as exc:
        raise DockerError(str(exc))
    if proc.returncode != 0:
        raise DockerError(proc.stderr.strip() or "docker failed")


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
