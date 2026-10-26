"""Whether a project is ready for implementation task work.

Init creates a valid factory skeleton. That is not the same as being ready
for an agent to implement source. `factory ready` reports the remaining
discovery, requirement, and planning gaps.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

from .constants import (
    ARTIFACTS_ROOT,
    SCAFFOLD_METADATA_PATH,
    SOURCE_STACK_AREAS,
    TASK_ROOT,
)
from .models import FactoryConfig, ProjectIntake


DISCOVERY_TASK_PREFIX = "TASK-0001"
_ACCEPTANCE_HEADING = re.compile(r"^##\s+Acceptance Criteria\s*$", re.MULTILINE)
_NEXT_HEADING = re.compile(r"^##\s+", re.MULTILINE)


@dataclass
class ReadinessReport:
    project_dir: Path
    gaps: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return not self.gaps


def _markdown_files(directory: Path, pattern: str) -> List[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        path
        for path in directory.glob(pattern)
        if path.is_file() and path.name != ".gitkeep"
    )


def _task_files(project_dir: Path, state: str) -> List[Path]:
    return _markdown_files(project_dir / TASK_ROOT / state, "*.md")


def _is_discovery_task(path: Path) -> bool:
    return path.name.startswith(DISCOVERY_TASK_PREFIX)


def _acceptance_criteria(text: str) -> List[str]:
    match = _ACCEPTANCE_HEADING.search(text)
    if not match:
        return []
    rest = text[match.end() :]
    next_heading = _NEXT_HEADING.search(rest)
    section = rest[: next_heading.start()] if next_heading else rest
    items: List[str] = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            item = stripped[2:].strip()
            if item:
                items.append(item)
    return items


def _discovery_in_backlog(project_dir: Path) -> bool:
    return any(_is_discovery_task(path) for path in _task_files(project_dir, "backlog"))


def _requirement_files(project_dir: Path) -> List[Path]:
    return _markdown_files(project_dir / ARTIFACTS_ROOT, "REQ-*.md")


def _implementable_todo_tasks(project_dir: Path) -> List[Path]:
    ready: List[Path] = []
    for path in _task_files(project_dir, "todo"):
        if _is_discovery_task(path):
            continue
        if _acceptance_criteria(path.read_text(encoding="utf-8")):
            ready.append(path)
    return ready


def _approved_source_stack(project_dir: Path) -> List[str]:
    intake_path = project_dir / ".factory-state" / "intake" / "project-specs-input.yaml"
    if not intake_path.is_file():
        return []
    try:
        intake = ProjectIntake.from_yaml(intake_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    approved: List[str] = []
    for area in SOURCE_STACK_AREAS:
        choice = intake.tech_stack.get(area)
        if choice is not None and choice.value.strip() and choice.status == "Approved":
            approved.append(f"{area}={choice.value}")
    return approved


def inspect_readiness(project_dir: Path) -> ReadinessReport:
    report = ReadinessReport(project_dir)
    if _discovery_in_backlog(project_dir):
        report.gaps.append(
            "discovery TASK-0001 is still in backlog; confirm project context first"
        )
    requirements = _requirement_files(project_dir)
    if not requirements:
        report.gaps.append(
            "no requirement artifact (REQ-*) under .factory-state/artifacts/"
        )
    else:
        report.notes.append(f"{len(requirements)} requirement artifact(s)")
    todo = _implementable_todo_tasks(project_dir)
    if not todo:
        report.gaps.append(
            "no non-discovery task in todo with acceptance criteria"
        )
    else:
        report.notes.append(
            f"{len(todo)} todo task(s) with acceptance criteria"
        )
    approved = _approved_source_stack(project_dir)
    if approved and not (project_dir / SCAFFOLD_METADATA_PATH).is_file():
        report.gaps.append(
            "approved source stack has no published scaffold "
            f"({', '.join(approved)}); record why source generation is skipped"
        )
    config_path = project_dir / ".factory-state" / "factory.yaml"
    if config_path.is_file():
        try:
            FactoryConfig.from_yaml(config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            report.gaps.append(f"invalid factory config: {exc}")
    return report


def readiness_problems(project_dir: Path) -> Tuple[List[str], List[str]]:
    """Return (errors, warnings). Gaps are warnings for `factory validate`."""
    report = inspect_readiness(project_dir)
    if report.ready:
        return [], []
    return [], [f"not ready for implementation: {gap}" for gap in report.gaps]


def render_readiness(report: ReadinessReport) -> str:
    lines: List[str] = []
    if report.ready:
        lines.append("Project is ready for implementation task work.")
    else:
        lines.append("Project is not ready for implementation task work:")
        for gap in report.gaps:
            lines.append(f"  - {gap}")
    if report.notes:
        if report.ready:
            for note in report.notes:
                lines.append(f"  - {note}")
        else:
            lines.append("Recorded so far:")
            for note in report.notes:
                lines.append(f"  - {note}")
    if not report.ready:
        lines.append(
            "Next: finish TASK-0001, convert specs with onboard-specs or "
            "create-requirement, then plan-tasks. Re-run `factory ready`."
        )
    return "\n".join(lines)
