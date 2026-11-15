"""Docker sandbox for imported repository code.

The daemon mounts only the import directory (read-write) and a copy of the runner
(read-only). The image root is read-only. The process gets a fresh environment,
never the server's. ``--env-file`` is a host path so secret values stay out of the
``docker`` argv.
"""
from __future__ import annotations
import os, re, shutil, subprocess, threading, uuid
from typing import Callable, Dict, List, Optional

RUNNER_IN_CONTAINER = "/opt/studio-runner/runner.py"
_KEY = re.compile(r"^[A-Z][A-Z0-9_]*$")
_BLOCKED = {"JWT_SECRET", "STUDIO_SECRET_KEY", "DATABASE_URL", "REDIS_URL", "STUDIO_DB"}


class DockerMissing(Exception):
    pass


_MAC_DOCKER = "/Applications/Docker.app/Contents/Resources/bin/docker"


def docker_exe() -> str:
    """``docker`` on PATH, or Docker Desktop's bundled CLI when that app is installed but the shell PATH is not.

    Returns the bare name ``docker`` when neither is available. ``_popen`` then reports DockerMissing.
    """
    found = shutil.which("docker")
    if found:
        return found
    if os.path.isfile(_MAC_DOCKER) and os.access(_MAC_DOCKER, os.X_OK):
        return _MAC_DOCKER
    return "docker"


def allow_secret(key: str) -> bool:
    """A name the sandbox may receive. Server credentials and STUDIO_* never qualify."""
    return bool(_KEY.fullmatch(key or "")) and key not in _BLOCKED and not key.startswith("STUDIO_")


def sandbox_env(home: str, secrets: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = {
        "HOME": home,
        "PYTHONUNBUFFERED": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
        "PIP_CACHE_DIR": os.path.join(home, ".cache", "pip"),
        "GIT_TERMINAL_PROMPT": "0",
    }
    for key, value in (secrets or {}).items():
        if not allow_secret(key) or value is None: continue
        text = str(value)
        if "\n" in text or "\x00" in text: continue
        env[key] = text
    return env


def host_path(path: str, root: str, host_root: Optional[str]) -> str:
    """Path the Docker daemon can mount. Inside Compose, ``root`` is the container path
    and ``host_root`` is the same directory on the host."""
    path, root = os.path.realpath(path), os.path.realpath(root)
    if host_root and (path == root or path.startswith(root + os.sep)):
        return os.path.join(os.path.abspath(host_root), os.path.relpath(path, root))
    return path


def _write_env(path: str, env: Dict[str, str]) -> None:
    lines = [f"{k}={v}" for k, v in env.items()]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    os.chmod(path, 0o600)


def _locked(name: str, network: str, memory: str, cpus: str, pids: int) -> List[str]:
    """``docker run`` with the limits every sandbox shares: read-only root, no capabilities, small /tmp."""
    return [
        docker_exe(), "run", "--rm", "-i", "--name", name, "--init",
        "--network", network,
        "--memory", memory, "--memory-swap", memory,
        "--cpus", str(cpus), "--pids-limit", str(pids),
        "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges:true",
        "--tmpfs", "/tmp:rw,nosuid,size=64m",
        "--stop-timeout", "1",
        "--user", f"{os.getuid()}:{os.getgid()}",
    ]


def build_code(*, name: str, image: str, command: List[str], memory: str, cpus: str, pids: int,
               environment: Optional[Dict[str, str]] = None) -> List[str]:
    """Tool node Code mode: no network, no mounts, and a fixed environment that holds no secret.
    `environment` comes from the language; Python's is the default."""
    fixed = environment if environment is not None else {"HOME": "/tmp", "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    env = [x for k, v in fixed.items() for x in ("-e", f"{k}={v}")]
    return _locked(name, "none", memory, cpus, pids) + env + ["-w", "/tmp", image] + command


def build(*, name: str, image: str, job_dir: str, cwd: str, command: List[str], env: Dict[str, str],
          network: str, memory: str, cpus: str, pids: int, runner_dir: Optional[str],
          root: str, host_root: Optional[str]) -> List[str]:
    job_dir = os.path.realpath(job_dir)
    env_file = os.path.join(job_dir, ".sandbox.env")
    _write_env(env_file, env)
    argv = _locked(name, network, memory, cpus, pids) + [
        "-v", f"{host_path(job_dir, root, host_root)}:{job_dir}:rw",
        "--env-file", host_path(env_file, root, host_root),
        "-w", cwd,
    ]
    if runner_dir:
        argv += ["-v", f"{host_path(os.path.realpath(runner_dir), root, host_root)}:/opt/studio-runner:ro"]
    argv.append(image)
    argv.extend(command)
    return argv


def container_name() -> str:
    return "lgs" + uuid.uuid4().hex[:12]


def failure_event(returncode: Optional[int], timed_out: bool, timeout: int, stderr: str) -> Optional[dict]:
    """Error event when the sandbox was killed for time or memory. None when it exited on its own."""
    if not timed_out and returncode != 137: return None
    why = f"time limit ({timeout}s)" if timed_out else "memory limit"
    tail = (stderr or "").strip()[-400:]
    return {"type": "error", "errors": [f"Sandbox stopped ({why}). {tail}".strip()]}


class Child:
    """A ``docker run`` (or any Popen) whose stderr is drained so a chatty daemon cannot deadlock."""

    def __init__(self, proc: subprocess.Popen, name: Optional[str]):
        self._p, self.name = proc, name
        self.stdout = proc.stdout
        self._err: List[str] = []
        self._t = threading.Thread(target=self._drain, daemon=True)
        self._t.start()

    def _drain(self):
        if self._p.stderr: self._err.append(self._p.stderr.read() or "")

    def kill(self):
        if self.name:
            subprocess.run([docker_exe(), "kill", self.name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if self._p.poll() is None: self._p.kill()

    def wait(self):
        self._p.wait(); self._t.join(timeout=2)

    @property
    def returncode(self) -> Optional[int]:
        return self._p.returncode

    def stderr_text(self) -> str:
        self._t.join(timeout=2)
        return "".join(self._err)


def _popen(argv: List[str]) -> subprocess.Popen:
    try:
        return subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    except FileNotFoundError:
        raise DockerMissing("Docker is not available on this server") from None


def captured(argv: List[str], *, name: str, timeout: int) -> tuple[str, str, int, bool]:
    """Run to completion. On timeout, kill the named container and report timed_out."""
    proc = _popen(argv)
    try:
        out, err = proc.communicate(timeout=timeout)
        return out or "", err or "", proc.returncode or 0, False
    except subprocess.TimeoutExpired as exc:
        subprocess.run([docker_exe(), "kill", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
        if proc.poll() is None: proc.kill()
        out = exc.stdout or ""
        err = exc.stderr or ""
        if isinstance(out, bytes): out = out.decode(errors="replace")
        if isinstance(err, bytes): err = err.decode(errors="replace")
        return out, err, 137, True


def start(argv: List[str], *, name: str) -> Child:
    return Child(_popen(argv), name)


def local_child(argv: List[str], **kwargs) -> Child:
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **kwargs)
    return Child(proc, None)


def kill_of(child: Child) -> Callable[[], None]:
    return child.kill
