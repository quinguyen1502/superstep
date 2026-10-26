"""Artifact ID uniqueness checks and next-free allocation.

Artifact IDs (``TASK-0001``, ``REV-0001``, ...) are sequential per type, but
parallel agent sessions each allocate "the next free number" against their own
branch snapshot, so concurrent tasks race and collide once merged. These
helpers let agents verify uniqueness against the working tree, any set of
fetched refs, or the union of all of them — before pushing, not after.

Which refs to scan is the whole question. An ID is free only when *no branch*
holds it, and work sits in unmerged branches for days: a scan of the
integration branch alone cannot see a number a sibling session allocated an
hour ago and has not merged. Allocation therefore wants every ref
(``--all-refs``); a pre-merge check wants at least the branch being merged
into.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from .constants import (
    ARCHIVE_ROOT,
    ARTIFACTS_ROOT,
    DECISIONS_ROOT,
    TASK_ROOT,
)
from .errors import FactoryError

# Roots that hold ID-named artifacts. Archived tasks and companion artifacts
# stay included: reusing an archived number is still a collision.
ID_ROOTS = (TASK_ROOT, ARTIFACTS_ROOT, DECISIONS_ROOT, ARCHIVE_ROOT)

# `TYPE-NNNN` filename prefix, e.g. `TASK-0123-title.md`, `REV-0080-task-id.md`.
_ID_PREFIX = re.compile(r"^([A-Z][A-Z0-9]*)-(\d+)(?=[-.])")

_PAD_WIDTH = 4

# Refs named in scope messages before they are summarised as a count.
_SCOPE_NAME_LIMIT = 3


def _git(project_dir: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=project_dir,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:  # git missing entirely
        raise FactoryError(f"Cannot run git: {exc}") from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or f"git {' '.join(args)} failed"
        raise FactoryError(detail)
    return result.stdout


def all_refs(project_dir: Path) -> List[str]:
    """Every local and remote branch, which is what "no branch holds it" means.

    ``origin/HEAD`` and friends are symbolic aliases for a branch already in
    the list, so they are dropped rather than scanned twice.
    """
    output = _git(
        project_dir,
        "for-each-ref",
        "--format=%(refname)",
        "refs/heads",
        "refs/remotes",
    )
    refs = [line.strip() for line in output.splitlines() if line.strip()]
    return [ref for ref in refs if not ref.endswith("/HEAD")]


def _scan_tree(project_dir: Path) -> Set[str]:
    """Basenames of ID-bearing files in the working tree."""
    names: Set[str] = set()
    for root in ID_ROOTS:
        base = project_dir / root
        if not base.is_dir():
            continue
        for path in base.rglob("*"):
            if path.is_file() and _ID_PREFIX.match(path.name):
                names.add(path.name)
    return names


def _scan_ref(project_dir: Path, ref: str) -> Set[str]:
    """Basenames of ID-bearing files at a git ref (e.g. ``origin/develop``)."""
    output = _git(project_dir, "ls-tree", "-r", "--name-only", ref, "--", *ID_ROOTS)
    names: Set[str] = set()
    for line in output.splitlines():
        name = line.rsplit("/", 1)[-1]
        if name and _ID_PREFIX.match(name):
            names.add(name)
    return names


WORKING_TREE = "working tree"


def _gather(project_dir: Path, refs: Sequence[str] = ()) -> Dict[str, Set[str]]:
    """Map each ID-bearing basename to the places holding it.

    Where a name lives is what tells a resolved collision from a live one: a
    pair whose second half exists only on one abandoned branch was renumbered
    long ago, and reporting the filenames alone leaves the reader to go and
    find that out by hand.
    """
    sources: Dict[str, Set[str]] = defaultdict(set)
    for name in _scan_tree(project_dir):
        sources[name].add(WORKING_TREE)
    for ref in refs:
        for name in _scan_ref(project_dir, ref):
            sources[name].add(ref)
    if not sources and not (project_dir / TASK_ROOT).is_dir() and not refs:
        raise FactoryError(f"Not a factory project repository: {project_dir}")
    return sources


def collect_ids(
    project_dir: Path, refs: Sequence[str] = ()
) -> Dict[Tuple[str, int], Set[str]]:
    """Map ``(type, number)`` to the distinct basenames that claim it.

    Lifecycle moves change an artifact's directory but keep its basename, so
    grouping by basename never flags a task travelling ``backlog -> done`` on
    only one side of a ref comparison. Two *different* artifacts sharing one
    number always differ in slug, hence in basename, and are flagged.
    """
    claims: Dict[Tuple[str, int], Set[str]] = defaultdict(set)
    for name in _gather(project_dir, refs):
        match = _ID_PREFIX.match(name)
        assert match is not None  # filtered during scanning
        claims[(match.group(1), int(match.group(2)))].add(name)
    return claims


def duplicate_ids(
    project_dir: Path, refs: Sequence[str] = ()
) -> List[Tuple[str, int, List[str]]]:
    """IDs claimed by more than one distinct artifact, sorted by type/number."""
    return sorted(
        (kind, number, sorted(names))
        for (kind, number), names in collect_ids(project_dir, refs).items()
        if len(names) > 1
    )


def next_ids(
    project_dir: Path,
    types: Sequence[str] = (),
    refs: Sequence[str] = (),
) -> List[Tuple[str, str]]:
    """Next free ID per type, over the union of working tree and ``refs``."""
    highest: Dict[str, int] = defaultdict(int)
    for (kind, number), _names in collect_ids(project_dir, refs).items():
        highest[kind] = max(highest[kind], number)
    wanted: Iterable[str] = [t.upper() for t in types] if types else sorted(highest)
    return [
        (kind, f"{kind}-{highest[kind] + 1:0{_PAD_WIDTH}d}") for kind in wanted
    ]


def _resolve_refs(
    project_dir: Path, refs: Optional[Sequence[str]], scan_all: bool
) -> List[str]:
    """Refs to scan, with ``--all-refs`` unioned onto any explicit ``--ref``."""
    resolved = list(refs or ())
    if scan_all:
        for ref in all_refs(project_dir):
            if ref not in resolved:
                resolved.append(ref)
    return resolved


def _describe_scope(refs: Sequence[str], scan_all: bool) -> str:
    if not refs:
        return "working tree"
    if scan_all or len(refs) > _SCOPE_NAME_LIMIT:
        return f"working tree + {len(refs)} refs"
    return f"working tree + {', '.join(refs)}"


def _describe_sources(sources: Set[str]) -> str:
    """Where a name lives, shortened — ref names are long and mostly prefix."""
    if not sources:
        return ""
    ordered = sorted(sources, key=lambda s: (s != WORKING_TREE, s))
    shown = [s.replace("refs/remotes/", "").replace("refs/heads/", "") for s in ordered]
    if len(shown) > _SCOPE_NAME_LIMIT:
        rest = len(shown) - _SCOPE_NAME_LIMIT
        return f"{', '.join(shown[:_SCOPE_NAME_LIMIT])} (+{rest} more)"
    return ", ".join(shown)


def check_ids_command(
    project_dir: Path,
    refs: Optional[Sequence[str]] = None,
    scan_all: bool = False,
) -> int:
    try:
        resolved = _resolve_refs(project_dir, refs, scan_all)
        sources = _gather(project_dir, resolved)
        duplicates = duplicate_ids(project_dir, resolved)
    except FactoryError as exc:
        print(f"factory: {exc}")
        return 2
    scope = _describe_scope(resolved, scan_all)
    if not duplicates:
        print(f"Artifact IDs are unique ({scope}).")
        return 0
    print(f"Duplicate artifact IDs ({scope}):")
    for kind, number, names in duplicates:
        print(f"  {kind}-{number:0{_PAD_WIDTH}d}:")
        for name in names:
            where = _describe_sources(sources.get(name, set()))
            print(f"    {name}" + (f"  [{where}]" if where else ""))
    print(
        "Renumber the later allocation (and its cross-references) before "
        "pushing; keep the earlier-merged artifact's number."
    )
    if resolved:
        print(
            "A pair held only by branches that will never merge was renumbered "
            "already; the record that moved keeps a Renumbered: line."
        )
    return 1


def _add_scan_arguments(parser: argparse.ArgumentParser, allocating: bool) -> None:
    parser.add_argument(
        "--ref",
        action="append",
        default=None,
        help="Also include a git ref (e.g. origin/develop). Repeatable.",
    )
    parser.add_argument(
        "--all-refs",
        action="store_true",
        help=(
            "Include every local and remote branch. An ID is free only when no "
            "branch holds it, so allocation should use this."
            if allocating
            else "Include every local and remote branch, not just --ref."
        ),
    )
    parser.add_argument("-C", "--project-dir", default=".")


def configure_ids_parser(parser: argparse.ArgumentParser) -> None:
    """Define the `ids` subcommands on ``parser``.

    Shared by the full CLI and by the light entry point in ``entry``, which
    dispatches `ids` without importing the rest of the CLI. One definition
    because two would drift, and the flags here are the ones an agent is told
    to run before every push.
    """
    subcommands = parser.add_subparsers(dest="ids_command")
    check = subcommands.add_parser(
        "check", help="Fail when any TYPE-NNNN ID names more than one artifact."
    )
    _add_scan_arguments(check, allocating=False)
    allocate = subcommands.add_parser(
        "next", help="Print the next free ID per artifact type."
    )
    allocate.add_argument(
        "types", nargs="*", help="Artifact types to allocate (e.g. TASK REV QA)."
    )
    _add_scan_arguments(allocate, allocating=True)


def run_ids(args: Any) -> int:
    """Dispatch a parsed `ids` invocation. Returns the process exit code."""
    project_dir = Path(args.project_dir).resolve()
    if args.ids_command == "check":
        return check_ids_command(
            project_dir=project_dir, refs=args.ref, scan_all=args.all_refs
        )
    if args.ids_command == "next":
        return next_ids_command(
            project_dir=project_dir,
            types=args.types,
            refs=args.ref,
            scan_all=args.all_refs,
        )
    print("factory: ids needs a subcommand: check or next")
    return 2


def next_ids_command(
    project_dir: Path,
    types: Sequence[str] = (),
    refs: Optional[Sequence[str]] = None,
    scan_all: bool = False,
) -> int:
    try:
        resolved = _resolve_refs(project_dir, refs, scan_all)
        allocations = next_ids(project_dir, types, resolved)
    except FactoryError as exc:
        print(f"factory: {exc}")
        return 2
    for _kind, allocated in allocations:
        print(allocated)
    if not allocations:
        print("No ID-bearing artifacts found.")
    return 0
