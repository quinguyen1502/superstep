from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class ConfigurationOutput:
    path: str
    content: bytes
    configurator_id: str

    @property
    def text(self) -> str:
        return self.content.decode("utf-8")


@dataclass
class ConfigurationAction:
    path: str
    status: str
    reason: str
    output: Optional[ConfigurationOutput] = None
    existing_sha256: Optional[str] = None


@dataclass
class ConfigurationPlan:
    project_dir: str
    source_sha256: str
    configurators: List[str] = field(default_factory=list)
    actions: List[ConfigurationAction] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def conflicts(self) -> List[ConfigurationAction]:
        return [action for action in self.actions if action.status == "conflict"]

    @property
    def invalid(self) -> List[ConfigurationAction]:
        return [action for action in self.actions if action.status == "invalid"]

    @property
    def ready(self) -> bool:
        return bool(self.configurators) and not self.errors and not self.invalid

    def render(self) -> str:
        lines = [f"Stack configuration plan: {self.project_dir}"]
        if self.configurators:
            lines.append("  Configurators:")
            lines.extend(f"    - {item}" for item in self.configurators)
        else:
            lines.append("  Configurators: none")
        lines.extend(
            f"  {action.status.upper():8} {action.path} - {action.reason}"
            for action in self.actions
        )
        lines.extend(f"  ERROR    {message}" for message in self.errors)
        lines.extend(f"  WARN     {message}" for message in self.warnings)
        return "\n".join(lines)
