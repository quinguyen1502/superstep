"""Enable `python -m factory_cli` as a clean CLI entry point."""

from __future__ import annotations

import sys

from .main import main

if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
