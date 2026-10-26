from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from .constants import (
    ARCHIVE_TASK_ROOT,
    FACTORY_CONFIG_PATH,
    TASK_ROOT,
    TASK_STATES,
)
from .models import FactoryConfig
from .project import FactoryError
from .storage import StoreError, open_store
from .storage.base import parse_task_markdown


def _load_config(project_dir: Path) -> Optional[FactoryConfig]:
    config_path = project_dir / FACTORY_CONFIG_PATH
    if not config_path.is_file():
        return None
    try:
        return FactoryConfig.from_yaml(config_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def open_task_store(project_dir: Path):
    return open_store(project_dir, _load_config(project_dir))


def create_task(project_dir: Path, task_id: str, title: str, state: str) -> int:
    try:
        store = open_task_store(project_dir)
        record = store.create_task(task_id, title, state)
        print(f"Created task: {record.path or record.task_id}")
        return 0
    except (FactoryError, StoreError) as exc:
        print(f"factory: {exc}")
        return 2


def move_task(project_dir: Path, task_id: str, target_state: str) -> int:
    try:
        store = open_task_store(project_dir)
        before = store.get_task(task_id)
        record = store.move_task(task_id, target_state)
        origin = before.state if before else "?"
        print(f"Moved task: {record.task_id} {origin} -> {record.state}")
        return 0
    except (FactoryError, StoreError) as exc:
        print(f"factory: {exc}")
        return 2


def archive_tasks(
    project_dir: Path, state: str = "done", task_id: Optional[str] = None
) -> int:
    """Move completed task files out of the board into an archive folder."""
    try:
        if state not in TASK_STATES:
            raise FactoryError(f"Invalid task state: {state}")
        source_dir = project_dir / TASK_ROOT / state
        if not source_dir.is_dir():
            raise FactoryError(f"Not a factory project repository: {project_dir}")
        pattern = f"{task_id}*.md" if task_id else "*.md"
        sources = sorted(source_dir.glob(pattern))
        if not sources:
            scope = f" matching {task_id}" if task_id else ""
            print(f"No {state} tasks to archive{scope}.")
            return 0
        destination_dir = project_dir / ARCHIVE_TASK_ROOT / state
        destination_dir.mkdir(parents=True, exist_ok=True)
        archived_ids: List[str] = []
        from .locks import LockTimeout, project_lock

        try:
            with project_lock(project_dir):
                for source in sources:
                    destination = destination_dir / source.name
                    if destination.exists():
                        raise FactoryError(f"Archived task already exists: {destination}")
                    parsed_id, _ = parse_task_markdown(
                        source.name, source.read_text(encoding="utf-8")
                    )
                    source.replace(destination)
                    archived_ids.append(parsed_id)
                    print(f"Archived: {source.relative_to(project_dir)}")
        except LockTimeout as exc:
            raise FactoryError(str(exc)) from exc
        # Keep any database mirror consistent with the folder source of truth.
        try:
            open_task_store(project_dir).forget(archived_ids)
        except StoreError:
            pass
        print(f"Archived {len(archived_ids)} task(s) to {ARCHIVE_TASK_ROOT}/{state}.")
        return 0
    except (FactoryError, StoreError) as exc:
        print(f"factory: {exc}")
        return 2


def validate_task_state(state: str) -> None:
    if state not in TASK_STATES:
        raise FactoryError(f"Invalid task state: {state}")


def validate_project_task_root(project_dir: Path) -> None:
    if not (project_dir / TASK_ROOT).is_dir():
        raise FactoryError(f"Not a factory project repository: {project_dir}")
    for state in TASK_STATES:
        if not (project_dir / TASK_ROOT / state).is_dir():
            raise FactoryError(f"Missing task state directory: {TASK_ROOT}/{state}")


def find_task_files(project_dir: Path, task_id: str) -> List[Path]:
    matches: List[Path] = []
    for state in TASK_STATES:
        matches.extend(sorted((project_dir / TASK_ROOT / state).glob(f"{task_id}*.md")))
    return matches
