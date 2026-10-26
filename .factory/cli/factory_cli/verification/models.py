from __future__ import annotations

import shlex
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class VerificationCheck:
    check_id: str
    kind: str
    working_dir: str
    argv: List[str]
    source: str

    @property
    def command_display(self) -> str:
        return shlex.join(self.argv)

    def to_dict(self) -> Dict[str, object]:
        return {
            "check_id": self.check_id,
            "kind": self.kind,
            "working_dir": self.working_dir,
            "command": self.command_display,
            "source": self.source,
        }


@dataclass
class VerificationPlan:
    project_dir: str
    source_sha256: str
    profile: str = "quick"
    checks: List[VerificationCheck] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    origin: str = "discovery"
    selected_kinds: Tuple[str, ...] = ()
    fingerprint: str = ""

    @property
    def ready(self) -> bool:
        return bool(self.checks) and not self.errors

    def render(self) -> str:
        lines = [
            f"Verification plan: {self.project_dir}",
            f"  Profile: {self.profile}",
        ]
        for check in self.checks:
            lines.extend(
                (
                    f"  READY       {check.check_id} ({check.kind})",
                    f"    cwd: {check.working_dir}",
                    f"    command: {check.command_display}",
                    f"    source: {check.source}",
                )
            )
        lines.extend(f"  ERROR       {message}" for message in self.errors)
        lines.extend(f"  WARN        {message}" for message in self.warnings)
        return "\n".join(lines)


@dataclass(frozen=True)
class VerificationResult:
    check: VerificationCheck
    status: str
    returncode: Optional[int]
    started_at: str
    duration_seconds: float
    output: str = ""
    error: str = ""

    def to_dict(self) -> Dict[str, object]:
        return {
            **self.check.to_dict(),
            "status": self.status,
            "returncode": self.returncode,
        }
