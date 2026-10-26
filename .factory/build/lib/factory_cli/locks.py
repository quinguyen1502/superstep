"""A best-effort advisory lock to serialize task mutations on one checkout.

Two processes editing the same project (e.g. a board save while a CLI move runs)
can race on file renames. An ``flock`` on ``.factory-state/.factory.lock`` makes
those mutations mutually exclusive on a single machine. On platforms without
``fcntl`` the lock is a no-op (multi-process editing there is not supported).
"""
from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path
from typing import Iterator

try:
    import fcntl

    _HAS_FCNTL = True
except ImportError:  # pragma: no cover - non-POSIX platforms
    _HAS_FCNTL = False

LOCK_NAME = ".factory.lock"


class LockTimeout(Exception):
    """Raised when the project lock cannot be acquired within the timeout."""


def _ensure_gitignored(state_dir: Path) -> None:
    gitignore = state_dir / ".gitignore"
    existing = (
        gitignore.read_text(encoding="utf-8").splitlines()
        if gitignore.is_file()
        else []
    )
    if LOCK_NAME in existing:
        return
    lines = existing + [LOCK_NAME] if existing else [LOCK_NAME]
    try:
        gitignore.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:  # pragma: no cover - read-only checkout
        pass


@contextlib.contextmanager
def project_lock(project_dir: Path, timeout: float = 10.0) -> Iterator[None]:
    state_dir = Path(project_dir) / ".factory-state"
    state_dir.mkdir(parents=True, exist_ok=True)
    _ensure_gitignored(state_dir)
    if not _HAS_FCNTL:
        yield
        return
    lock_path = state_dir / LOCK_NAME
    handle = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
    try:
        deadline = time.monotonic() + timeout
        while True:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise LockTimeout(
                        "Timed out waiting for the project lock; another factory "
                        "process may be writing to this project."
                    )
                time.sleep(0.05)
        yield
    finally:
        try:
            fcntl.flock(handle, fcntl.LOCK_UN)
        finally:
            os.close(handle)
