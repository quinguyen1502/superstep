"""Factory pipeline milestones for onboarding and status.

A Factory project moves through a handful of well-defined stages: init,
optional source scaffolding, dependency install, verification, stack
configuration, and then the task lifecycle (backlog → done). Each stage
leaves a durable marker under ``.factory-state/`` so the shell can detect
its state without asking anyone.

This module names the stages, teaches the shell how to detect their
state, and links each stage to the ``Action`` a newcomer should run next.
The shell renders it as ``/pipeline`` — a snapshot that answers "what is
this thing, and where am I in it?" without needing to read docs first.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from ..constants import (
    CONFIGURATION_METADATA_PATH,
    CONFIGURATION_ROOT,
    DEPENDENCY_METADATA_PATH,
    DEPENDENCY_ROOT,
    FACTORY_CONFIG_PATH,
    SCAFFOLD_METADATA_PATH,
    SCAFFOLD_ROOT,
    TASK_STATES,
    VERIFICATION_METADATA_PATH,
    VERIFICATION_ROOT,
)


class StageStatus(str, Enum):
    """Where a milestone sits for this project.

    ``DONE`` means the stage published its marker artifact and no
    ``INCOMPLETE`` sits alongside it. ``IN_PROGRESS`` means the ``plan``
    ran but the ``apply`` did not finish (marker + INCOMPLETE both present,
    or INCOMPLETE only). ``NOT_STARTED`` means no marker at all.
    """

    DONE = "done"
    IN_PROGRESS = "in_progress"
    NOT_STARTED = "not_started"


@dataclass(frozen=True)
class Stage:
    id: str
    label: str
    summary: str          # one-line explanation for newcomers
    marker: str           # relative path checked for DONE
    incomplete: Optional[str]  # relative path checked for IN_PROGRESS
    next_action: str      # Action.id to run when NOT_STARTED
    docs: str             # docs/*.md reference
    optional: bool = False


@dataclass
class StageEvaluation:
    stage: Stage
    status: StageStatus
    detail: str


# Order matters: this is the *canonical* pipeline sequence a newcomer
# should follow. The Tasks stage is a checkpoint, not a build phase, but
# putting it at the end explains where the pre-task work leads.
STAGES: Tuple[Stage, ...] = (
    Stage(
        id="init",
        label="Init",
        summary="Create the project intake, standards, and initial task.",
        marker=FACTORY_CONFIG_PATH,
        incomplete=None,
        next_action="init",
        docs="docs/cli.md#project-initialization",
    ),
    Stage(
        id="scaffold",
        label="Scaffold",
        summary="Generate the source baseline for approved stack choices.",
        marker=SCAFFOLD_METADATA_PATH,
        incomplete=f"{SCAFFOLD_ROOT}/INCOMPLETE",
        next_action="scaffold.plan",
        docs="docs/scaffolding.md",
        optional=True,
    ),
    Stage(
        id="deps",
        label="Dependencies",
        summary="Install project-local dependencies from lockfiles or manifests.",
        marker=DEPENDENCY_METADATA_PATH,
        incomplete=f"{DEPENDENCY_ROOT}/INCOMPLETE",
        next_action="deps.plan",
        docs="docs/dependencies.md",
        optional=True,
    ),
    Stage(
        id="verify",
        label="Verify",
        summary="Run deterministic checks (test/lint/typecheck/build) and record evidence.",
        marker=VERIFICATION_METADATA_PATH,
        incomplete=None,
        next_action="verify.plan",
        docs="docs/verification.md",
        optional=True,
    ),
    Stage(
        id="stack",
        label="Stack config",
        summary="Publish CI/Compose configuration derived from approved decisions.",
        marker=CONFIGURATION_METADATA_PATH,
        incomplete=f"{CONFIGURATION_ROOT}/INCOMPLETE",
        next_action="stack.plan",
        docs="docs/stack-configuration.md",
        optional=True,
    ),
    Stage(
        id="tasks",
        label="Tasks",
        summary="Move work through backlog → todo → doing → review → qa → done.",
        marker="",  # dynamic — evaluated separately below
        incomplete=None,
        next_action="board",
        docs="docs/task-lifecycle.md",
    ),
)


def _status_for(project_dir: Path, stage: Stage) -> StageEvaluation:
    if stage.id == "tasks":
        return _tasks_status(project_dir, stage)
    marker_path = project_dir / stage.marker if stage.marker else None
    marker_exists = marker_path.is_file() if marker_path else False
    incomplete_exists = (
        (project_dir / stage.incomplete).exists() if stage.incomplete else False
    )
    if incomplete_exists and not marker_exists:
        return StageEvaluation(
            stage,
            StageStatus.IN_PROGRESS,
            f"INCOMPLETE marker present at {stage.incomplete}",
        )
    if incomplete_exists and marker_exists:
        return StageEvaluation(
            stage,
            StageStatus.IN_PROGRESS,
            "artifact published but INCOMPLETE marker still exists — resolve proposals",
        )
    if marker_exists:
        return StageEvaluation(stage, StageStatus.DONE, str(stage.marker))
    return StageEvaluation(
        stage,
        StageStatus.NOT_STARTED,
        f"no {stage.marker} yet" if stage.marker else "not started",
    )


def _tasks_status(project_dir: Path, stage: Stage) -> StageEvaluation:
    """Tasks is a checkpoint, not a milestone: report a friendly summary.

    Any task at all counts as IN_PROGRESS; if every task is in ``done``
    (or the archive is present) we mark it DONE so a project that has
    completed all its scoped work reads cleanly.
    """
    counts = {state: 0 for state in TASK_STATES}
    tasks_root = project_dir / ".factory-state" / "tasks"
    if not tasks_root.is_dir():
        return StageEvaluation(stage, StageStatus.NOT_STARTED, "no tasks folder yet")
    for state in TASK_STATES:
        folder = tasks_root / state
        if folder.is_dir():
            counts[state] = sum(1 for path in folder.iterdir() if path.suffix == ".md")
    total = sum(counts.values())
    if total == 0:
        return StageEvaluation(stage, StageStatus.NOT_STARTED, "no tasks yet")
    open_tasks = total - counts["done"]
    detail = "  ".join(f"{state}:{counts[state]}" for state in TASK_STATES)
    if open_tasks == 0:
        return StageEvaluation(stage, StageStatus.DONE, detail)
    return StageEvaluation(stage, StageStatus.IN_PROGRESS, detail)


def evaluate(project_dir: Path) -> List[StageEvaluation]:
    """Return one :class:`StageEvaluation` per pipeline stage."""
    return [_status_for(project_dir, stage) for stage in STAGES]


def suggest_next(evaluations: List[StageEvaluation]) -> Optional[StageEvaluation]:
    """Pick the earliest not-started or in-progress stage.

    ``IN_PROGRESS`` beats ``NOT_STARTED`` at the same position because a
    partially-run stage should be finished before starting the next one.
    Skips optional stages that are ``NOT_STARTED`` when a later required
    stage is already done — that means the owner intentionally skipped it.
    """
    for evaluation in evaluations:
        if evaluation.status is StageStatus.IN_PROGRESS:
            return evaluation
    for evaluation in evaluations:
        if evaluation.status is StageStatus.NOT_STARTED:
            if evaluation.stage.optional and _later_stage_done(evaluations, evaluation):
                continue
            return evaluation
    return None


def _later_stage_done(
    evaluations: List[StageEvaluation],
    target: StageEvaluation,
) -> bool:
    seen = False
    for evaluation in evaluations:
        if evaluation.stage.id == target.stage.id:
            seen = True
            continue
        if seen and evaluation.status is StageStatus.DONE:
            return True
    return False
