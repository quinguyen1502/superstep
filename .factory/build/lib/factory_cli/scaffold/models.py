from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class ScaffoldTarget:
    area: str
    technology: str

    @property
    def label(self) -> str:
        return f"{self.area}: {self.technology}"


@dataclass(frozen=True)
class AdapterPreview:
    adapter_id: str
    adapter_version: int
    targets: List[ScaffoldTarget]
    available: bool
    command: List[str] = field(default_factory=list)
    expected_paths: List[str] = field(default_factory=list)
    reason: str = ""

    @property
    def command_display(self) -> str:
        return shlex.join(self.command) if self.command else "deterministic adapter"


@dataclass
class ScaffoldPlan:
    project_dir: str
    source_sha256: str
    targets: List[ScaffoldTarget] = field(default_factory=list)
    context_targets: List[ScaffoldTarget] = field(default_factory=list)
    adapters: List[AdapterPreview] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return bool(self.adapters) and not self.errors and all(
            adapter.available for adapter in self.adapters
        )

    def render(self) -> str:
        lines = [f"Scaffold plan: {self.project_dir}"]
        if self.targets:
            lines.append("  Approved scaffold targets:")
            lines.extend(f"    - {target.label}" for target in self.targets)
        else:
            lines.append("  Approved scaffold targets: none")
        if self.context_targets:
            lines.append("  Approved context decisions:")
            lines.extend(f"    - {target.label}" for target in self.context_targets)
        for adapter in self.adapters:
            status = "READY" if adapter.available else "UNAVAILABLE"
            lines.append(f"  {status:11} {adapter.adapter_id} v{adapter.adapter_version}")
            lines.append(f"    command: {adapter.command_display}")
            if adapter.expected_paths:
                lines.append("    expected paths:")
                lines.extend(f"      - {path}" for path in adapter.expected_paths)
            if adapter.reason:
                lines.append(f"    note: {adapter.reason}")
        lines.extend(f"  ERROR       {message}" for message in self.errors)
        lines.extend(f"  WARN        {message}" for message in self.warnings)
        return "\n".join(lines)


@dataclass(frozen=True)
class ScaffoldOutput:
    path: str
    content: bytes
    adapter_id: str
    executable: bool = False

    @property
    def is_text(self) -> bool:
        try:
            self.content.decode("utf-8")
        except UnicodeDecodeError:
            return False
        return True

    @property
    def text(self) -> Optional[str]:
        if not self.is_text:
            return None
        return self.content.decode("utf-8")


@dataclass
class ScaffoldAction:
    path: str
    status: str
    reason: str
    output: Optional[ScaffoldOutput] = None
    existing_sha256: Optional[str] = None
    existing_executable: Optional[bool] = None


@dataclass
class ScaffoldPublishPlan:
    project_dir: str
    source_sha256: str
    adapters: List[AdapterPreview]
    actions: List[ScaffoldAction] = field(default_factory=list)

    @property
    def conflicts(self) -> List[ScaffoldAction]:
        return [action for action in self.actions if action.status == "conflict"]

    @property
    def invalid(self) -> List[ScaffoldAction]:
        return [action for action in self.actions if action.status == "invalid"]

    def render(self) -> str:
        lines = [f"Scaffold publish plan: {self.project_dir}"]
        lines.extend(
            f"  {action.status.upper():8} {action.path} - {action.reason}"
            for action in self.actions
        )
        return "\n".join(lines)
