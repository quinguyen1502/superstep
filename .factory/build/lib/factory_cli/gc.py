"""Compact finished factory-state without deleting history.

``factory gc`` moves old ``done`` tasks off the board and, by default, their
companion ``REV`` / ``QA`` / ``SUM`` artifacts with them. Files stay in git
under ``.factory-state/archive/``. IDs remain reserved. Requirements,
decisions, standards, and live tasks are never moved.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

from .constants import (
    ARCHIVE_ARTIFACT_ROOT,
    ARCHIVE_TASK_ROOT,
    ARTIFACTS_ROOT,
    GC_COMPANION_TYPES,
    GC_DEFAULT_KEEP,
    TASK_ROOT,
    TASK_STATES,
)
from .errors import FactoryError
from .locks import LockTimeout, project_lock
from .storage import StoreError
from .tasks import open_task_store


_ID_PREFIX = re.compile(r"^([A-Z][A-Z0-9]*)-(\d+)(?=[-.])")
_TASK_TOKEN = re.compile(r"\bTASK-\d+\b")


@dataclass(frozen=True)
class GcMove:
    source: str
    destination: str


@dataclass
class GcPlan:
    project_dir: Path
    keep: int
    with_artifacts: bool
    task_counts: Dict[str, int] = field(default_factory=dict)
    artifact_counts: Dict[str, int] = field(default_factory=dict)
    archived_task_count: int = 0
    archived_artifact_count: int = 0
    keep_names: List[str] = field(default_factory=list)
    moves: List[GcMove] = field(default_factory=list)
    forgotten_ids: List[str] = field(default_factory=list)

    @property
    def task_moves(self) -> List[GcMove]:
        prefix = f"{ARCHIVE_TASK_ROOT}/"
        return [move for move in self.moves if move.destination.startswith(prefix)]

    @property
    def artifact_moves(self) -> List[GcMove]:
        prefix = f"{ARCHIVE_ARTIFACT_ROOT}/"
        return [move for move in self.moves if move.destination.startswith(prefix)]


def _id_parts(name: str) -> Optional[Tuple[str, int, str]]:
    match = _ID_PREFIX.match(name)
    if not match:
        return None
    kind, number = match.group(1), match.group(2)
    return kind, int(number), f"{kind}-{number}"


def _task_sort_key(path: Path) -> Tuple[int, str]:
    parsed = _id_parts(path.name)
    number = parsed[1] if parsed else -1
    return number, path.name


def _count_md(directory: Path) -> int:
    if not directory.is_dir():
        return 0
    return sum(1 for path in directory.glob("*.md") if path.is_file())


def _counts_by_type(directory: Path) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    if not directory.is_dir():
        return {}
    for path in directory.glob("*.md"):
        if not path.is_file():
            continue
        parsed = _id_parts(path.name)
        counts[parsed[0] if parsed else "other"] += 1
    return dict(sorted(counts.items()))


def _task_id_from_name(name: str) -> Optional[str]:
    parsed = _id_parts(name)
    if parsed is None or parsed[0] != "TASK":
        return None
    return parsed[2]


def _live_task_ids(project_dir: Path, keep_names: Sequence[str]) -> Set[str]:
    live: Set[str] = set()
    for state in TASK_STATES:
        if state == "done":
            continue
        directory = project_dir / TASK_ROOT / state
        if not directory.is_dir():
            continue
        for path in directory.glob("*.md"):
            task_id = _task_id_from_name(path.name)
            if task_id:
                live.add(task_id)
    for name in keep_names:
        task_id = _task_id_from_name(name)
        if task_id:
            live.add(task_id)
    return live


def _task_tokens(path: Path) -> Set[str]:
    tokens = set(_TASK_TOKEN.findall(path.name))
    try:
        tokens.update(_TASK_TOKEN.findall(path.read_text(encoding="utf-8")))
    except OSError:
        pass
    return tokens


def _companion_moves(
    project_dir: Path,
    archived_task_ids: Set[str],
    live_task_ids: Set[str],
) -> List[GcMove]:
    artifacts = project_dir / ARTIFACTS_ROOT
    if not artifacts.is_dir():
        return []
    destination_dir = ARCHIVE_ARTIFACT_ROOT
    moves: List[GcMove] = []
    for path in sorted(artifacts.glob("*.md")):
        if not path.is_file():
            continue
        parsed = _id_parts(path.name)
        if parsed is None or parsed[0] not in GC_COMPANION_TYPES:
            continue
        tokens = _task_tokens(path)
        if tokens & live_task_ids:
            continue
        if not (tokens & archived_task_ids):
            continue
        source = f"{ARTIFACTS_ROOT}/{path.name}"
        destination = f"{destination_dir}/{path.name}"
        if (project_dir / destination).exists():
            raise FactoryError(f"Archived artifact already exists: {destination}")
        moves.append(GcMove(source, destination))
    return moves


def plan_gc(
    project_dir: Path,
    keep: int = GC_DEFAULT_KEEP,
    with_artifacts: bool = True,
) -> GcPlan:
    if keep < 0:
        raise FactoryError("--keep must be >= 0")
    done_dir = project_dir / TASK_ROOT / "done"
    if not (project_dir / TASK_ROOT).is_dir() or not done_dir.is_dir():
        raise FactoryError(f"Not a factory project repository: {project_dir}")

    done_files = sorted(
        (path for path in done_dir.glob("*.md") if path.is_file()),
        key=_task_sort_key,
    )
    keep_files = done_files[-keep:] if keep else []
    archive_files = done_files[:-keep] if keep else done_files
    keep_names = [path.name for path in keep_files]
    forgotten_ids: List[str] = []
    moves: List[GcMove] = []
    for path in archive_files:
        destination = f"{ARCHIVE_TASK_ROOT}/done/{path.name}"
        if (project_dir / destination).exists():
            raise FactoryError(f"Archived task already exists: {destination}")
        task_id = _task_id_from_name(path.name)
        if task_id:
            forgotten_ids.append(task_id)
        moves.append(GcMove(f"{TASK_ROOT}/done/{path.name}", destination))

    archived_task_ids = set(forgotten_ids)
    if with_artifacts and archived_task_ids:
        live = _live_task_ids(project_dir, keep_names)
        moves.extend(_companion_moves(project_dir, archived_task_ids, live))

    task_counts = {
        state: _count_md(project_dir / TASK_ROOT / state) for state in TASK_STATES
    }
    return GcPlan(
        project_dir=project_dir,
        keep=keep,
        with_artifacts=with_artifacts,
        task_counts=task_counts,
        artifact_counts=_counts_by_type(project_dir / ARTIFACTS_ROOT),
        archived_task_count=_count_md(project_dir / ARCHIVE_TASK_ROOT / "done"),
        archived_artifact_count=_count_md(project_dir / ARCHIVE_ARTIFACT_ROOT),
        keep_names=keep_names,
        moves=moves,
        forgotten_ids=forgotten_ids,
    )


def render_gc_plan(plan: GcPlan, apply: bool = False) -> str:
    lines = [
        f"Factory state: {plan.project_dir}",
        "  tasks:",
    ]
    width = max((len(state) for state in TASK_STATES), default=4)
    for state in TASK_STATES:
        lines.append(f"    {state:<{width}}  {plan.task_counts.get(state, 0)}")
    artifact_total = sum(plan.artifact_counts.values())
    lines.append(f"  artifacts: {artifact_total}")
    for kind, count in plan.artifact_counts.items():
        lines.append(f"    {kind:<{width}}  {count}")
    lines.append("  archive:")
    lines.append(f"    tasks      {plan.archived_task_count}")
    lines.append(f"    artifacts  {plan.archived_artifact_count}")
    lines.append("")
    lines.append(f"Plan (keep last {plan.keep} done task(s)):")
    if plan.keep_names:
        preview = plan.keep_names[0]
        if len(plan.keep_names) > 1:
            preview = f"{plan.keep_names[0]} ... {plan.keep_names[-1]}"
        lines.append(f"  keep     {len(plan.keep_names)}  {preview}")
    else:
        lines.append("  keep     0")
    lines.append(
        f"  archive  {len(plan.task_moves)} task(s) -> {ARCHIVE_TASK_ROOT}/done/"
    )
    if plan.with_artifacts:
        lines.append(
            "  archive  "
            f"{len(plan.artifact_moves)} artifact(s) -> {ARCHIVE_ARTIFACT_ROOT}/"
        )
    else:
        lines.append("  artifacts left in place (--no-artifacts)")
    lines.append("")
    if apply:
        lines.append("Writing archive.")
    else:
        lines.append("Dry run; pass --apply to write. Files are moved, not deleted.")
    return "\n".join(lines)


def apply_gc_plan(plan: GcPlan) -> int:
    if not plan.moves:
        print("Nothing to archive.")
        return 0
    try:
        with project_lock(plan.project_dir):
            for move in plan.moves:
                source = plan.project_dir / move.source
                destination = plan.project_dir / move.destination
                if not source.is_file():
                    raise FactoryError(f"Source disappeared: {move.source}")
                if destination.exists():
                    raise FactoryError(
                        f"Archived file already exists: {move.destination}"
                    )
                destination.parent.mkdir(parents=True, exist_ok=True)
                source.replace(destination)
                print(f"Archived: {move.source} -> {move.destination}")
    except LockTimeout as exc:
        raise FactoryError(str(exc)) from exc
    if plan.forgotten_ids:
        try:
            open_task_store(plan.project_dir).forget(plan.forgotten_ids)
        except StoreError:
            pass
    print(
        f"Archived {len(plan.task_moves)} task(s) and "
        f"{len(plan.artifact_moves)} artifact(s)."
    )
    return 0


def run_gc(
    project_dir: Path,
    keep: int = GC_DEFAULT_KEEP,
    with_artifacts: bool = True,
    apply: bool = False,
) -> int:
    plan = plan_gc(project_dir, keep=keep, with_artifacts=with_artifacts)
    print(render_gc_plan(plan, apply=apply))
    if not apply:
        return 0
    return apply_gc_plan(plan)
