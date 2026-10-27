"""Tool node Code mode (TASK-0053, REQ-0039, DEC-0041): user Python runs in a separate process, never in this one.

`run_code` sends {source, state} to the language's runner (`code_languages`, TASK-0079) on stdin and reads one JSON result line. The server only
parses the source (`problems`); it never executes it. A call is killed at its time limit or when the run is cancelled.
- docker (default): a fresh container with no network, no mounts, an empty environment, memory/CPU/process limits.
- subprocess (TASK-0056, STUDIO_CODE_RUNTIME=subprocess): a child of this server with an empty environment, a temporary
  working directory and (on Linux) rlimits. It is NOT isolation: the code can use the network and read what the server
  user can read. It exists only for servers without Docker, and every surface labels it.
- remote (STUDIO_CODE_RUNTIME=remote): the same subprocess runtime, but inside a separate sandbox service
  (`app.sandbox_service`, docker/studio-sandbox) that holds no studio secrets, reached over HTTP with a shared token.
Each runtime is a `CodeRunner` (strategy) in `RUNNERS`; `run_code` and `unavailable` only talk to that interface."""
from __future__ import annotations
import json, os, queue, re, signal, subprocess, sys, tempfile, threading, time
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional
from .issues import Issue
from ..core import config
from ..core.errors import AppError
from ..core.logging import get_logger
from . import code_languages as langs
from .sandbox import container, remote

SOURCE_MAX = 64 * 1024
STATE_MAX = 1024 * 1024
RESULT_MAX = 1024 * 1024
STDOUT_MAX = 64 * 1024
RUNNER = os.path.join(langs.SANDBOX, "code_runner.py")  # the Python runner
STARTER = langs.LANGUAGES["python"].starter  # kept for callers from before TASK-0079
_slots: Dict[int, threading.BoundedSemaphore] = {}
_checked: Dict[str, tuple[float, Optional[str]]] = {}  # image -> (when, problem or None)
CHECK_TTL = 30.0


@dataclass
class CodeResult:
    value: Any
    stdout: str = ""
    runtime: str = "docker"
    duration_ms: float = 0.0

    def trace(self) -> Dict[str, Any]:
        return {"stdout": self.stdout, "runtime": self.runtime, "duration_ms": self.duration_ms}


class CodeFailure(AppError):
    """An AppError that also carries what the code printed and its traceback, for the trace."""

    def __init__(self, code: str, output: Dict[str, Any], **params):
        AppError.__init__(self, code, **params); self.output = output


def problems(source: Any, language: Optional[str] = None) -> List[str]:
    """Why this source cannot run, from reading it alone (it is never executed here). Empty when it can."""
    lang = language or langs.DEFAULT
    if lang not in langs.enabled(): return [Issue("CODE_LANGUAGE_OFF", language=lang)]
    if not isinstance(source, str) or not source.strip(): return [Issue("CODE_EMPTY")]
    if len(source.encode()) > SOURCE_MAX: return [Issue("CODE_TOO_LARGE", kb=SOURCE_MAX // 1024)]
    return langs.LANGUAGES[lang].problems(source)


_first = threading.Lock(); _announced = False


def claim_first_unisolated_call() -> bool:
    """True exactly once per server process: the first Code call while the runtime is `subprocess` (for the audit log)."""
    global _announced
    with _first:
        if _announced: return False
        _announced = True; return True


def warn_if_unisolated() -> None:
    """One start-up WARNING when Code nodes run on the host without isolation (TASK-0056)."""
    if config.code_runtime() == "subprocess":
        get_logger("code").warning("Code nodes run directly on this host, WITHOUT Docker limiting their access "
                                   "(STUDIO_CODE_RUNTIME=subprocess): user code can use the network and read files the server user can read. Use Docker for anything but trusted local use.")


def unavailable(language: Optional[str] = None) -> Optional[str]:
    """Why Code nodes (of `language`, Python by default) cannot run here right now, or None."""
    if config.demo_mode(): return "demo"
    runtime = config.code_runtime()
    if runtime == "off": return "off"
    lang = language or langs.DEFAULT
    if lang not in langs.enabled(): return f"{lang} is not enabled (STUDIO_CODE_LANGUAGES)"
    return RUNNERS[runtime].problem(langs.LANGUAGES[lang])


def runtime_error(language: Optional[str] = None) -> Optional[AppError]:
    why = unavailable(language)
    if why is None: return None
    if why == "demo": return AppError("DEMO_CODE_DISABLED")
    return AppError("CODE_RUNTIME_OFF") if why == "off" else AppError("CODE_RUNTIME_UNAVAILABLE", reason=why)


def _slot() -> threading.BoundedSemaphore:
    n = config.code_concurrency()
    return _slots.setdefault(n, threading.BoundedSemaphore(n))


def _bytes(size: str) -> int:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kmg]?)b?\s*", (size or "").lower())
    if not m: return 256 * 1024 ** 2
    return int(float(m.group(1)) * 1024 ** "_kmg".index(m.group(2) or "_"))


def _rlimits(limits: List[tuple]) -> Callable[[], None]:
    def apply() -> None:  # runs in the child between fork and exec (Linux only)
        import resource
        for name, val in limits:
            try: resource.setrlimit(getattr(resource, name), (val, val))
            except (ValueError, OSError): pass
    return apply


def _drop_to(uid: int) -> Callable[[], None]:
    def apply() -> None:  # after the rlimits, in the child: no way back to the parent's user
        os.setgroups([]); os.setgid(uid); os.setuid(uid)
    return apply


def _host_process(workdir: str, seconds: float, lang: "langs.CodeLanguage", uid: Optional[int] = None) -> Dict[str, Any]:
    """Popen arguments for the subprocess runtime: empty environment, its own folder and process group, rlimits on Linux,
    and (when the parent is root, i.e. the sandbox service) its own unprivileged uid."""
    env = {"HOME": workdir, "TMPDIR": workdir, "PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", **lang.host_env(workdir)}
    kw: Dict[str, Any] = {"cwd": workdir, "env": env, "start_new_session": True}
    if sys.platform.startswith("linux"):
        limits = _rlimits(lang.host_rlimits(_bytes(config.code_memory()), int(seconds) + 1, config.code_pids()))
        if uid is None: kw["preexec_fn"] = limits
        else:
            os.chown(workdir, uid, uid); drop = _drop_to(uid)
            kw["preexec_fn"] = lambda: (limits(), drop())
    return kw


def _kill_group(proc: subprocess.Popen) -> None:
    try: os.killpg(proc.pid, signal.SIGKILL)  # the code and anything it started
    except (ProcessLookupError, PermissionError, OSError): pass


def _exchange(argv: List[str], name: str, payload: str, seconds: float,
              cancelled: Optional[Callable[[], bool]], popen: Optional[Dict[str, Any]] = None) -> tuple[str, str, int, str]:
    """Run to completion, or kill at the deadline or on cancel. Returns (stdout, stderr, returncode, stopped).
    `popen` set = the subprocess runtime (kill the process group); otherwise a `docker run` named `name`."""
    try: proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, **(popen or {}))
    except FileNotFoundError: raise AppError("CODE_RUNTIME_UNAVAILABLE", reason="Docker is not installed") from None
    box: Dict[str, Any] = {}
    t = threading.Thread(target=lambda: box.update(zip(("out", "err"), proc.communicate(payload))), daemon=True)
    t.start(); deadline = time.monotonic() + seconds; stopped = ""
    while t.is_alive():
        t.join(0.25)
        if not t.is_alive(): break
        if time.monotonic() >= deadline: stopped = "timeout"
        elif cancelled is not None and cancelled(): stopped = "cancelled"
        if stopped:
            if popen is not None: _kill_group(proc)
            else:
                try: subprocess.run([container.docker_exe(), "kill", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
                except (OSError, subprocess.TimeoutExpired): pass  # the local kill below still ends the client
            if proc.poll() is None: proc.kill()
            t.join(5); break
    return box.get("out") or "", box.get("err") or "", proc.returncode if proc.returncode is not None else -9, stopped


class CodeRunner:
    """Where one Code call executes. `problem`: why `lang` cannot run there now (None = it can). `exchange`: send the
    payload, return (stdout, stderr, returncode, stopped) with stopped in ("", "timeout", "cancelled")."""
    name = ""

    def problem(self, lang: "langs.CodeLanguage") -> Optional[str]: raise NotImplementedError

    def exchange(self, lang: "langs.CodeLanguage", payload: str, seconds: float,
                 cancelled: Optional[Callable[[], bool]]) -> tuple[str, str, int, str]: raise NotImplementedError


class DockerRunner(CodeRunner):
    """A fresh `docker run` per call: no network, no mounts, memory/CPU/process limits. Docker and the language's
    image are checked at most every 30 s."""
    name = "docker"

    def problem(self, lang):
        image = lang.image()
        hit = _checked.get(image)
        if hit and time.monotonic() - hit[0] < CHECK_TTL: return hit[1]
        try:
            r = subprocess.run([container.docker_exe(), "image", "inspect", image], stdout=subprocess.DEVNULL,
                               stderr=subprocess.PIPE, text=True, timeout=15)
            problem = None if r.returncode == 0 else (
                f"the image {image} is missing (build it: docker build -t {image} docker/studio-code)" if "No such image" in (r.stderr or "")
                else f"Docker is not running ({(r.stderr or '').strip()[:200]})")
        except FileNotFoundError: problem = "Docker is not installed"
        except subprocess.TimeoutExpired: problem = "Docker did not answer"
        _checked[image] = (time.monotonic(), problem)
        return problem

    def exchange(self, lang, payload, seconds, cancelled):
        name = container.container_name()
        argv = container.build_code(name=name, image=lang.image(), command=lang.command(), memory=config.code_memory(),
                                    cpus=config.code_cpus(), pids=config.code_pids(), environment=lang.container_env())
        return _exchange(argv, name, payload, seconds, cancelled)


class SubprocessRunner(CodeRunner):
    """A child process of this one (see the module docstring for what that does NOT isolate). With STUDIO_CODE_RUN_AS
    set and this process running as root, each concurrent call gets its own uid from that base (the sandbox service)."""
    name = "subprocess"

    def __init__(self) -> None: self._uids: Optional[queue.Queue] = None; self._lock = threading.Lock()

    def problem(self, lang): return lang.host_problem()

    def _uid_pool(self) -> Optional[queue.Queue]:
        base = config.code_run_as()
        if base is None or os.geteuid() != 0: return None
        with self._lock:
            if self._uids is None:
                self._uids = queue.Queue()
                for i in range(config.code_concurrency()): self._uids.put(base + i)
        return self._uids

    def exchange(self, lang, payload, seconds, cancelled):
        pool = self._uid_pool(); uid = pool.get() if pool is not None else None
        try:
            with tempfile.TemporaryDirectory(prefix="lgs-code-") as tmp:
                return _exchange(lang.host_command(tmp), "", payload, seconds, cancelled, _host_process(tmp, seconds, lang, uid))
        finally:
            if pool is not None: pool.put(uid)


class RemoteRunner(CodeRunner):
    """The sandbox service (STUDIO_SANDBOX_URL + STUDIO_SANDBOX_TOKEN); see engine/sandbox/remote.py."""
    name = "remote"

    def problem(self, lang): return remote.problem(lang.id)

    def exchange(self, lang, payload, seconds, cancelled): return remote.run(lang.id, payload, seconds, cancelled)


RUNNERS: Dict[str, CodeRunner] = {r.name: r for r in (DockerRunner(), SubprocessRunner(), RemoteRunner())}


def run_code(source: str, state: Dict[str, Any], *, node: str = "code", timeout: Optional[float] = None,
             cancelled: Optional[Callable[[], bool]] = None, language: Optional[str] = None) -> CodeResult:
    """Call main(state) of `source` once in the sandbox. Raises AppError (CodeFailure when the code itself failed)."""
    lang = langs.get(language, node)  # CODE_LANGUAGE_UNSUPPORTED before anything else
    if (err := runtime_error(lang.id)) is not None: raise err
    if (why := problems(source, lang.id)): raise AppError("CODE_INVALID", node=node, reason=why[0])
    data = json.dumps(state, ensure_ascii=False, default=str)
    if len(data.encode()) > STATE_MAX: raise AppError("CODE_TOO_LARGE", node=node, what="state", max_kb=STATE_MAX // 1024)
    limit = min(float(timeout), config.code_max_seconds()) if timeout else float(config.code_max_seconds())
    payload = json.dumps({"source": source, "stdout_max": STDOUT_MAX, "state": json.loads(data)}, ensure_ascii=False)
    runtime = config.code_runtime(); runner = RUNNERS[runtime]
    slot = _slot(); t0 = time.perf_counter()
    if not slot.acquire(timeout=limit): raise AppError("CODE_TIMEOUT", node=node, seconds=f"{limit:g}")
    try: out, err, code, stopped = runner.exchange(lang, payload, limit, cancelled)
    finally: slot.release()
    ms = round((time.perf_counter() - t0) * 1000, 2)
    if stopped == "timeout": raise CodeFailure("CODE_TIMEOUT", {"runtime": runtime}, node=node, seconds=f"{limit:g}")
    if stopped == "cancelled": raise AppError("CODE_FAILED", node=node, error="the run was cancelled")
    line = next((x for x in reversed(out.splitlines()) if x.strip()), "")
    if code in lang.memory_exit_codes and not line: raise CodeFailure("CODE_MEMORY", {"runtime": runtime}, node=node, limit=config.code_memory())
    if len(line.encode()) > RESULT_MAX + STDOUT_MAX: raise AppError("CODE_TOO_LARGE", node=node, what="result", max_kb=RESULT_MAX // 1024)
    try: res = json.loads(line)
    except ValueError:
        reason = (err or out).strip().splitlines()[-1:] or [f"exit code {code}"]
        if "Unable to find image" in err or "No such image" in err: _checked.pop(lang.image(), None)
        raise AppError("CODE_RUNTIME_UNAVAILABLE", reason=reason[0][:300]) from None
    output = {"stdout": res.get("stdout") or "", "runtime": runtime, "duration_ms": ms}
    if res.get("ok"): return CodeResult(res.get("value"), output["stdout"], runtime, ms)
    output["traceback"] = res.get("traceback") or ""
    kind = res.get("kind")
    if kind == "not_json": raise CodeFailure("CODE_RESULT_NOT_JSON", output, node=node, type=res.get("type") or "?")
    if kind == "invalid": raise CodeFailure("CODE_INVALID", output, node=node, reason=res.get("error") or "invalid code")
    raise CodeFailure("CODE_FAILED", output, node=node, error=(res.get("error") or "an error")[:300])

