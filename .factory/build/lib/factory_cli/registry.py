from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

import yaml

from .constants import FACTORY_CONFIG_PATH, FACTORY_STATE_DIR
from .project import FactoryError, atomic_write


@dataclass
class ProjectEntry:
    name: str
    path: str
    added_at: str

    def to_dict(self) -> dict:
        return {"name": self.name, "path": self.path, "added_at": self.added_at}


def factory_home() -> Path:
    """Global factory config directory, overridable for tests/isolation."""
    override = os.environ.get("FACTORY_HOME")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg).expanduser() / "factory"
    return Path.home() / ".factory"


def registry_path() -> Path:
    return factory_home() / "registry.yaml"


def _is_factory_project(path: Path) -> bool:
    return (path / FACTORY_STATE_DIR).is_dir() and (path / FACTORY_CONFIG_PATH).is_file()


def list_projects() -> List[ProjectEntry]:
    path = registry_path()
    if not path.is_file():
        return []
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or []
    if not isinstance(data, list):
        raise FactoryError(f"Invalid project registry: {path}")
    entries: List[ProjectEntry] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        entries.append(
            ProjectEntry(
                name=str(item.get("name", "")),
                path=str(item.get("path", "")),
                added_at=str(item.get("added_at", "")),
            )
        )
    return entries


def _save(entries: List[ProjectEntry]) -> None:
    atomic_write(
        registry_path(),
        yaml.safe_dump(
            [entry.to_dict() for entry in entries],
            sort_keys=False,
            allow_unicode=True,
        ),
    )


def add_project(project_dir: Path, name: Optional[str] = None) -> ProjectEntry:
    resolved = Path(project_dir).resolve()
    if not _is_factory_project(resolved):
        raise FactoryError(f"Not a factory project repository: {resolved}")
    entry_name = name or resolved.name
    entries = [item for item in list_projects() if Path(item.path) != resolved]
    if any(item.name == entry_name for item in entries):
        raise FactoryError(
            f"A different project is already registered as '{entry_name}'. "
            "Choose another name with --name."
        )
    entry = ProjectEntry(
        name=entry_name,
        path=str(resolved),
        added_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
    )
    entries.append(entry)
    _save(entries)
    return entry


def remove_project(name: str) -> bool:
    entries = list_projects()
    remaining = [item for item in entries if item.name != name]
    if len(remaining) == len(entries):
        return False
    _save(remaining)
    return True


def resolve_project(name: str) -> Path:
    for item in list_projects():
        if item.name == name:
            return Path(item.path)
    raise FactoryError(f"No registered project named: {name}")
