from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(frozen=True)
class DependencyCommand:
    target_id: str
    manager: str
    working_dir: str
    argv: List[str]
    manifest: str
    requires_network: bool = True
    expected_paths: List[str] = field(default_factory=list)
    integrity_argv: List[str] = field(default_factory=list)

    @property
    def command_display(self) -> str:
        return shlex.join(self.argv)

    def to_dict(self) -> Dict[str, object]:
        return {
            "target_id": self.target_id,
            "manager": self.manager,
            "working_dir": self.working_dir,
            "argv": list(self.argv),
            "manifest": self.manifest,
            "requires_network": self.requires_network,
            "expected_paths": list(self.expected_paths),
            "integrity_argv": list(self.integrity_argv),
        }


@dataclass
class DependencyPlan:
    project_dir: str
    source_sha256: str
    commands: List[DependencyCommand] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return bool(self.commands) and not self.errors

    @property
    def requires_network(self) -> bool:
        return any(command.requires_network for command in self.commands)

    def render(self) -> str:
        lines = [f"Dependency plan: {self.project_dir}"]
        for command in self.commands:
            lines.extend(
                (
                    f"  READY       {command.target_id} ({command.manager})",
                    f"    cwd: {command.working_dir}",
                    f"    command: {command.command_display}",
                    f"    network: {'required' if command.requires_network else 'not required'}",
                )
            )
            if command.integrity_argv:
                lines.append(
                    f"    integrity: {shlex.join(command.integrity_argv)}"
                )
        lines.extend(f"  ERROR       {message}" for message in self.errors)
        lines.extend(f"  WARN        {message}" for message in self.warnings)
        return "\n".join(lines)
