"""The installed `factory` command.

`ids` is dispatched here rather than in `main`, and the indirection earns its
keep: agents are required to run `factory ids` before every push that adds
artifacts, while importing `main` pulls in the adapter, model, and storage
stack — and with it PyYAML. A fresh checkout has none of that, so the one
mandatory pre-push command was the one command that could not run.

Nothing else is special-cased. Every other command wants the CLI anyway, and a
missing dependency there is a real missing dependency.
"""

from __future__ import annotations

import argparse
import sys
from typing import List, Optional


def main(argv: Optional[List[str]] = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if args[:1] == ["ids"]:
        return _run_ids(args[1:])
    from .main import main as run_cli

    return run_cli(args)


def _run_ids(argv: List[str]) -> int:
    # Imported inside, so the stdlib-only path stays stdlib-only.
    from .ids import configure_ids_parser, run_ids

    parser = argparse.ArgumentParser(
        prog="factory ids",
        description="Check artifact ID uniqueness or print next free IDs.",
    )
    configure_ids_parser(parser)
    return run_ids(parser.parse_args(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
