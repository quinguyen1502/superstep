"""Enable `python -m factory_cli` so the shell can spawn safe subprocesses.

The interactive hub captures stdout of READ actions by launching the CLI as a
subprocess. Keeping this entry point lets the child process run a clean
argparse loop without inheriting Textual's driver state from the parent.
"""

from __future__ import annotations

import sys

from .main import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
