"""Run a factory subcommand as a subprocess and capture its output.

The hub uses this for READ actions so their output can be shown in a modal
without leaving the Textual app. Spawning a fresh Python process keeps the
child argparse loop clean — no risk of Textual's driver intercepting the
child's stdout, and no accidental sharing of the parent's storage handles.
"""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass
class CommandResult:
    argv: Sequence[str]
    exit_code: int
    stdout: str
    stderr: str

    @property
    def ok(self) -> bool:
        return self.exit_code == 0

    @property
    def combined(self) -> str:
        parts = []
        if self.stdout.strip():
            parts.append(self.stdout.rstrip())
        if self.stderr.strip():
            parts.append("--- stderr ---")
            parts.append(self.stderr.rstrip())
        if not parts:
            parts.append("(no output)")
        return "\n".join(parts)


def run_factory(
    argv: Iterable[str],
    *,
    cwd: str | None = None,
    timeout: float | None = 60.0,
) -> CommandResult:
    """Invoke ``python -m factory_cli`` with ``argv`` and capture output.

    ``timeout`` guards against a subcommand that somehow hangs waiting for
    input; the caller sees a synthetic exit code instead of a stuck UI.
    """
    args = [sys.executable, "-m", "factory_cli", *list(argv)]
    env = dict(os.environ)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        completed = subprocess.run(
            args,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        return CommandResult(
            argv=list(argv),
            exit_code=124,
            stdout=exc.stdout or "",
            stderr=(exc.stderr or "") + f"\nCommand timed out after {timeout}s.",
        )
    except FileNotFoundError as exc:
        return CommandResult(
            argv=list(argv),
            exit_code=127,
            stdout="",
            stderr=f"Failed to launch factory: {exc}",
        )
    return CommandResult(
        argv=list(argv),
        exit_code=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
    )
