"""ShellContext: registry access and per-project overview snapshots.

The shell UI reads a :class:`ShellContext` to render both modes (global and
project). All computations are best-effort: a broken or partially-initialized
project must never crash the hub — errors are surfaced as an empty overview
plus a captured error message the UI can display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from ..constants import (
    CONFIGURATION_ROOT,
    DEPENDENCY_ROOT,
    FACTORY_CONFIG_PATH,
    METRICS_USAGE_JSONL,
    METRICS_USAGE_PATH,
    ORCHESTRATION_INCOMPLETE_PATH,
    ORCHESTRATION_METADATA_PATH,
    SCAFFOLD_ROOT,
    TASK_ROOT,
    TASK_STATES,
    TOOLING_ROOT,
)
from ..models import FactoryConfig
from ..registry import ProjectEntry, list_projects
from ..storage import StoreError, open_store


@dataclass
class ProjectOverview:
    """A snapshot of a project's shell-relevant state.

    ``task_counts`` is keyed by every element of :data:`TASK_STATES` even when
    a column is empty, so the UI can render a stable layout without checking
    for missing keys.
    """

    project_path: Path
    name: str
    storage_backend: str = "folder"
    task_counts: Dict[str, int] = field(default_factory=dict)
    over_budget: int = 0
    active_orchestrations: int = 0
    incomplete_areas: List[str] = field(default_factory=list)
    error: Optional[str] = None

    @property
    def total_open_tasks(self) -> int:
        return sum(
            count
            for state, count in self.task_counts.items()
            if state != "done"
        )


def _load_config(project_dir: Path) -> Optional[FactoryConfig]:
    config_path = project_dir / FACTORY_CONFIG_PATH
    if not config_path.is_file():
        return None
    try:
        return FactoryConfig.from_yaml(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _count_active_orchestrations(project_dir: Path) -> int:
    path = project_dir / ORCHESTRATION_METADATA_PATH
    if not path.is_file():
        return 0
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return 0
    active = data.get("active") if isinstance(data, dict) else None
    if isinstance(active, list):
        return len(active)
    # Fallback: some early versions stored assignments as top-level dict.
    if isinstance(data, dict):
        return sum(1 for value in data.values() if isinstance(value, dict))
    return 0


def _has_metrics(project_dir: Path) -> bool:
    return (
        (project_dir / METRICS_USAGE_JSONL).is_file()
        or (project_dir / METRICS_USAGE_PATH).is_file()
    )


_INCOMPLETE_MARKERS = (
    ("tooling", f"{TOOLING_ROOT}/INCOMPLETE"),
    ("scaffold", f"{SCAFFOLD_ROOT}/INCOMPLETE"),
    ("dependencies", f"{DEPENDENCY_ROOT}/INCOMPLETE"),
    ("stack", f"{CONFIGURATION_ROOT}/INCOMPLETE"),
    ("orchestration", ORCHESTRATION_INCOMPLETE_PATH),
    ("import", ".factory-state/import/INCOMPLETE"),
)


def _detect_incomplete(project_dir: Path) -> List[str]:
    return [
        area
        for area, relative in _INCOMPLETE_MARKERS
        if (project_dir / relative).exists()
    ]


def build_overview(entry: ProjectEntry) -> ProjectOverview:
    """Compute a :class:`ProjectOverview` for a registered project.

    Errors reading the project (missing config, corrupt storage) do not raise:
    they are captured in :attr:`ProjectOverview.error` so the hub can still
    render the project entry alongside a diagnostic message.
    """
    project_path = Path(entry.path)
    overview = ProjectOverview(project_path=project_path, name=entry.name)
    if not project_path.is_dir():
        overview.error = f"Project directory not found: {project_path}"
        return overview

    config = _load_config(project_path)
    overview.storage_backend = (
        getattr(config, "storage_backend", "folder") if config else "folder"
    )

    counts = {state: 0 for state in TASK_STATES}
    try:
        store = open_store(project_path, config)
        try:
            for record in store.list_tasks():
                if record.state in counts:
                    counts[record.state] += 1
        finally:
            close = getattr(store, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:  # noqa: BLE001 - closing is best-effort
                    pass
    except StoreError as exc:
        overview.error = str(exc)
    overview.task_counts = counts

    if config is not None and _has_metrics(project_path):
        try:
            store = open_store(project_path, config)
            try:
                overview.over_budget = sum(
                    1
                    for key, limit in config.budgets.items()
                    if store.usage_for_key(key) > limit
                )
            finally:
                close = getattr(store, "close", None)
                if callable(close):
                    try:
                        close()
                    except Exception:  # noqa: BLE001
                        pass
        except StoreError:
            # Storage backend already reported above; leave over_budget at 0.
            pass

    overview.active_orchestrations = _count_active_orchestrations(project_path)
    overview.incomplete_areas = _detect_incomplete(project_path)
    return overview


@dataclass
class ShellContext:
    """Holds the current shell mode and refreshable snapshots.

    A single instance is passed through the UI so widgets share one view of
    project state and can trigger :meth:`refresh` after any action that could
    have changed on-disk state.
    """

    projects: List[ProjectEntry] = field(default_factory=list)
    selected: Optional[ProjectEntry] = None
    overview: Optional[ProjectOverview] = None

    @classmethod
    def load(cls, preselected: Optional[Path] = None) -> "ShellContext":
        ctx = cls(projects=list_projects())
        if preselected is not None:
            resolved = preselected.resolve()
            match = next(
                (p for p in ctx.projects if Path(p.path).resolve() == resolved),
                None,
            )
            if match is None:
                # An unregistered but valid factory project — synthesize a
                # transient entry so the shell can still open it.
                match = ProjectEntry(name=resolved.name, path=str(resolved), added_at="")
            ctx.select(match)
        elif len(ctx.projects) == 1:
            ctx.select(ctx.projects[0])
        return ctx

    def select(self, entry: ProjectEntry) -> ProjectOverview:
        self.selected = entry
        self.overview = build_overview(entry)
        return self.overview

    def clear_selection(self) -> None:
        self.selected = None
        self.overview = None

    def refresh(self) -> None:
        """Recompute registry and, if a project is selected, its overview."""
        self.projects = list_projects()
        if self.selected is None:
            return
        current = next(
            (
                p
                for p in self.projects
                if Path(p.path).resolve() == Path(self.selected.path).resolve()
            ),
            self.selected,
        )
        self.selected = current
        self.overview = build_overview(current)
