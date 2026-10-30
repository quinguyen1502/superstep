"""OpenSSH for `deploy`. The remote host is not given a copy of this CLI."""
from __future__ import annotations

import shlex
import subprocess
from typing import Optional


class SshError(Exception):
    def __init__(self, message: str):
        self.message = message


class SshResult:
    def __init__(self, returncode: int, stdout: bytes, stderr: bytes):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class Ssh:
    """One remote account. `probe` is the call that must fail before any write."""

    def __init__(self, destination: str, port: Optional[int] = None):
        self.destination = destination
        self.port = port

    def probe(self) -> None:
        self._check(["true"])

    def home(self) -> str:
        result = self._check(["pwd"])
        text = result.stdout.decode("utf-8", "replace").strip()
        if not text.startswith("/"):
            raise SshError("ssh did not report a home directory")
        return text

    def read(self, path: str) -> Optional[bytes]:
        result = self.run(["cat", path])
        if result.returncode == 0:
            return result.stdout
        err = result.stderr.decode("utf-8", "replace").lower()
        if "no such file" in err or "not a directory" in err:
            return None
        raise SshError(result.stderr.decode("utf-8", "replace").strip() or "ssh failed")

    def mkdir(self, path: str, mode: int = 0o700) -> None:
        self._check(["mkdir", "-p", path])
        self._check(["chmod", f"{mode:03o}", path])

    def write(self, path: str, data: bytes, mode: int = 0o600) -> None:
        parent = path.rsplit("/", 1)[0] if "/" in path else "."
        self._check(["mkdir", "-p", parent])
        script = f"cat > {shlex.quote(path)} && chmod {mode:03o} {shlex.quote(path)}"
        result = self._exec(script, data)
        if result.returncode != 0:
            raise SshError(result.stderr.decode("utf-8", "replace").strip() or "ssh failed")

    def run(self, argv: list[str], stdin: Optional[bytes] = None) -> SshResult:
        remote = " ".join(shlex.quote(part) for part in argv)
        return self._exec(remote, stdin)

    def _check(self, argv: list[str]) -> SshResult:
        result = self.run(argv)
        if result.returncode != 0:
            raise SshError(result.stderr.decode("utf-8", "replace").strip() or "ssh failed")
        return result

    def _exec(self, remote: str, stdin: Optional[bytes]) -> SshResult:
        command = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=10",
            # BatchMode cannot show a prompt. A changed host key still fails.
            "-o", "StrictHostKeyChecking=accept-new",
        ]
        if self.port:
            command.extend(["-p", str(self.port)])
        command.extend(["--", self.destination, remote])
        try:
            proc = subprocess.run(command, input=stdin, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as exc:
            raise SshError(str(exc))
        return SshResult(proc.returncode, proc.stdout, proc.stderr)
