from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(frozen=True)
class OrchestratorAssignment:
    task_id: str
    task_title: str
    task_path: str
    tool_id: str
    branch: str
    worktree_path: str

    def to_dict(self) -> Dict[str, object]:
        return {
            "task_id": self.task_id,
            "task_title": self.task_title,
            "task_path": self.task_path,
            "tool_id": self.tool_id,
            "branch": self.branch,
            "worktree_path": self.worktree_path,
        }


@dataclass
class OrchestratorPlan:
    project_dir: str
    integration_branch: str
    available_tools: List[str] = field(default_factory=list)
    assignments: List[OrchestratorAssignment] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return bool(self.assignments) and not self.errors

    def render(self) -> str:
        lines = [
            f"Orchestration plan: {self.project_dir}",
            f"  Integration branch: {self.integration_branch}",
            f"  Available tools: {', '.join(self.available_tools) or '(none)'}",
        ]
        for assignment in self.assignments:
            lines.extend(
                (
                    f"  READY       {assignment.task_id} -> {assignment.tool_id}",
                    f"    title:    {assignment.task_title}",
                    f"    branch:   {assignment.branch}",
                    f"    worktree: {assignment.worktree_path}",
                )
            )
        lines.extend(f"  ERROR       {message}" for message in self.errors)
        lines.extend(f"  WARN        {message}" for message in self.warnings)
        return "\n".join(lines)


@dataclass(frozen=True)
class OrchestratorRecord:
    task_id: str
    tool_id: str
    branch: str
    worktree_path: str
    status: str
    created_at: str
    launch_command: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "task_id": self.task_id,
            "tool_id": self.tool_id,
            "branch": self.branch,
            "worktree_path": self.worktree_path,
            "status": self.status,
            "created_at": self.created_at,
            "launch_command": self.launch_command,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, object]) -> "OrchestratorRecord":
        return cls(
            task_id=str(data.get("task_id", "")),
            tool_id=str(data.get("tool_id", "")),
            branch=str(data.get("branch", "")),
            worktree_path=str(data.get("worktree_path", "")),
            status=str(data.get("status", "")),
            created_at=str(data.get("created_at", "")),
            launch_command=(
                str(data["launch_command"])
                if data.get("launch_command") is not None
                else None
            ),
        )
