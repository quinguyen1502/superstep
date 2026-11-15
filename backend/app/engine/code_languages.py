"""Languages of the Tool node Code mode: one strategy per language, one shared runner.

`code_runtime` owns everything every language shares: the payload on stdin, the limits, the deadline and cancel, the
one-line JSON result and the error codes. A `CodeLanguage` only says how to check a source without running it, which
command runs the language's runner (inside the container and on the host) and which image and packages it has.
Adding a language = one class here + one entry in `LANGUAGES`; nothing else branches on the language."""
from __future__ import annotations
import ast, base64, os, re, sys
from typing import Dict, List, Optional
from ..core import config
from ..core.errors import AppError

SANDBOX = os.path.join(os.path.dirname(__file__), "sandbox")
DEFAULT = "python"


def _read(name: str) -> str:
    with open(os.path.join(SANDBOX, name), encoding="utf-8") as fh: return fh.read()


class CodeLanguage:
    """The interface. Subclasses set `id`, `starter` and implement the four methods."""
    id: str = ""
    starter: str = ""

    def problems(self, source: str) -> List[str]:
        """Why `source` cannot run, from reading it alone (never executed on the server). Empty when it can."""
        raise NotImplementedError

    def command(self) -> List[str]:
        """argv inside the container (the runner travels on the command line; nothing is mounted)."""
        raise NotImplementedError

    def host_command(self, workdir: str) -> List[str]:
        """argv for the host subprocess runtime."""
        raise NotImplementedError

    def host_env(self, workdir: str) -> Dict[str, str]:
        """Extra environment for the host subprocess (on top of the empty base environment)."""
        return {}

    def image(self) -> str: raise NotImplementedError
    def packages(self) -> List[str]: raise NotImplementedError

    def container_env(self) -> Dict[str, str]:
        """The fixed environment inside the container. It never holds a secret."""
        return {"HOME": "/tmp"}

    def host_rlimits(self, memory: int, seconds: int, pids: int) -> List[tuple]:
        """(resource name, value) pairs applied to the host subprocess (Linux)."""
        return [("RLIMIT_CPU", seconds), ("RLIMIT_NOFILE", 64)]

    memory_exit_codes: tuple = (137, -9)  # exit codes that mean "out of memory" when no result line came

    def host_problem(self) -> Optional[str]:
        """Why the host subprocess runtime cannot run this language (e.g. its binary is missing), or None."""
        return None


class Python(CodeLanguage):
    id = "python"
    starter = 'def main(state):\n    """Return the value for the output field."""\n    return state.get("message", "")\n'

    def problems(self, source: str) -> List[str]:
        try: tree = ast.parse(source, "<code>")
        except SyntaxError as e: return [f"syntax error on line {e.lineno}: {e.msg}"]
        mains = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "main"]
        if not mains: return ["define a top-level function main(state)"]
        a = mains[-1].args
        if len(a.posonlyargs) + len(a.args) < 1 and a.vararg is None: return ["main must take the state as its argument: main(state)"]
        return []

    def command(self) -> List[str]: return ["python", "-I", "-c", _read("code_runner.py")]
    def host_command(self, workdir: str) -> List[str]: return [sys.executable, "-I", "-c", _read("code_runner.py")]
    def host_env(self, workdir: str) -> Dict[str, str]:
        env = {"PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1"}
        return {**env, "STUDIO_CODE_NO_NETWORK": "1"} if config.code_no_network() else env  # read by code_runner.py
    def container_env(self) -> Dict[str, str]: return {"HOME": "/tmp", "PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1"}
    def image(self) -> str: return config.code_image()
    def packages(self) -> List[str]: return config.code_packages()

    def host_rlimits(self, memory: int, seconds: int, pids: int) -> List[tuple]:
        return [("RLIMIT_AS", memory), ("RLIMIT_CPU", seconds), ("RLIMIT_NOFILE", 64), ("RLIMIT_NPROC", pids)]


MAIN_TS = re.compile(r"^\s*export\s+(?:(?:async\s+)?function\s*\*?\s*main\s*\(|(?:const|let|var)\s+main\b)|"
                     r"^\s*export\s*\{[^}]*\bmain\b[^}]*\}", re.M)
IMPORT_TS = re.compile(r"""(?:\bfrom\s*|^\s*import\s*|\bimport\s*\(\s*)(["'])([^"'\n]+)\1""", re.M)
COMMENTS_TS = re.compile(r"""("(?:\\.|[^"\\\n])*"|'(?:\\.|[^'\\\n])*'|`(?:\\.|[^`\\])*`)|/\*.*?\*/|//[^\n]*""", re.S)  # strings kept


class TypeScript(CodeLanguage):
    """TypeScript (and JavaScript) on Deno, transpiled without type checking.
    Deno runs with no permission at all, so even the host runtime cannot read files, open sockets, read the
    environment or start processes; the V8 heap is capped at the memory limit."""
    id = "typescript"
    starter = ('export function main(state: State) {\n'
               '  // Return the value for the output field. Packages: import { z } from "npm:zod@3"\n'
               '  return state.message ?? ""\n'
               '}\n')
    memory_exit_codes = (137, -9, 133, -5)  # V8 "out of memory" aborts with SIGTRAP (133 / -5)

    def problems(self, source: str) -> List[str]:
        code = COMMENTS_TS.sub(lambda m: m.group(1) or " ", source)
        if not MAIN_TS.search(code): return ["export a function main(state): export function main(state) { … }"]
        allowed = self.packages()
        for _q, spec in IMPORT_TS.findall(code):
            if (why := import_problem(spec, allowed)): return [why]
        return []

    def _deno_args(self) -> List[str]:
        mb = max(32, int(_mib(config.code_memory()) * 0.75))
        runner = base64.b64encode(_read("code_runner.ts").encode()).decode()
        return ["run", "--quiet", "--no-prompt", "--no-remote", "--no-config", "--no-lock", "--cached-only",
                f"--v8-flags=--max-old-space-size={mb}", f"data:application/typescript;base64,{runner}"]

    def command(self) -> List[str]: return ["deno", *self._deno_args()]
    def host_command(self, workdir: str) -> List[str]: return [config.deno_exe() or "deno", *self._deno_args()]

    def host_env(self, workdir: str) -> Dict[str, str]:
        return {"NO_COLOR": "1", "DENO_NO_UPDATE_CHECK": "1", "DENO_DIR": config.code_ts_deno_dir() or os.path.join(workdir, ".deno")}

    def container_env(self) -> Dict[str, str]: return {"HOME": "/tmp", "NO_COLOR": "1", "DENO_NO_UPDATE_CHECK": "1"}
    def image(self) -> str: return config.code_ts_image()
    def packages(self) -> List[str]:
        """The allowlist. On the host runtime the packages must be in STUDIO_CODE_TS_DENO_DIR, so without one there are
        none unless STUDIO_CODE_TS_PACKAGES says otherwise."""
        if config.code_runtime() == "subprocess" and not config.code_ts_deno_dir() and os.environ.get("STUDIO_CODE_TS_PACKAGES") is None:
            return []
        return config.code_ts_packages()

    def host_rlimits(self, memory: int, seconds: int, pids: int) -> List[tuple]:
        # No RLIMIT_AS (V8 reserves far more address space than it uses; the heap cap above limits memory) and no
        # RLIMIT_NPROC (it counts every process of the server user, Deno needs threads, and it cannot start processes).
        return [("RLIMIT_CPU", seconds), ("RLIMIT_NOFILE", 256)]

    def host_problem(self) -> Optional[str]:
        exe = config.deno_exe()
        return None if exe and os.access(exe, os.X_OK) else "Deno is not installed (install deno or set STUDIO_DENO)"


SPEC_TS = re.compile(r"^((?:npm|jsr):(?:@[^/@]+/)?[^/@]+)(?:@([^/]*))?(/.*)?$")


def import_problem(spec: str, allowed: List[str]) -> Optional[str]:
    """Why `spec` may not be imported, or None. Allowed entries are pinned `name@major` (``npm:zod@3``); an import
    must use the same name and major: ``npm:zod@3``, ``npm:zod@3.25.1`` or ``npm:zod@3/mini``. An unversioned
    ``npm:zod`` would make Deno pick the newest version, which the cache need not have, so it is refused too."""
    m = SPEC_TS.match(spec)
    for entry in allowed:
        e = SPEC_TS.match(entry)
        if not (m and e) or m.group(1) != e.group(1): continue
        want = e.group(2)
        if want is None: return None if m.group(2) is None else f'import "{spec}": use "{entry}" (no version)'
        have = m.group(2)
        if have is not None and (have == want or have.startswith(want + ".")): return None
        if have is None: return f'import "{spec}" needs a version: use "{entry}"'
        return f'import "{spec}": version {have} is not available, use "{entry}"'
    return f'import "{spec}" is not available' + (f" (allowed: {', '.join(allowed)})" if allowed else " (no packages are allowed here)")


def _mib(size: str) -> int:
    m = re.fullmatch(r"\s*(\d+(?:\.\d+)?)\s*([kmg]?)b?\s*", (size or "").lower())
    if not m: return 256
    return int(float(m.group(1)) * 1024 ** "_kmg".index(m.group(2) or "_") / 1024 ** 2)


LANGUAGES: Dict[str, CodeLanguage] = {"python": Python(), "typescript": TypeScript()}


def language_of(data: Optional[dict]) -> str:
    """The language of a Code-mode node's data; graphs saved have none and are Python."""
    return str((data or {}).get("language") or DEFAULT)


def enabled() -> List[str]:
    """Languages this server offers: STUDIO_CODE_LANGUAGES (comma-separated) filtered to the known ones."""
    return [x for x in config.code_languages() if x in LANGUAGES]


def get(language: Optional[str], node: str = "code") -> CodeLanguage:
    """The strategy for `language`, or CODE_LANGUAGE_UNSUPPORTED when it is unknown or not enabled here."""
    lang = language or DEFAULT
    if lang not in enabled(): raise AppError("CODE_LANGUAGE_UNSUPPORTED", node=node, language=lang)
    return LANGUAGES[lang]
