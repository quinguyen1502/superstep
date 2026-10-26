from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from .clarification import clarification_problems
from .constants import (
    FACTORY_CONFIG_PATH,
    REQUIRED_PROJECT_PATHS,
    STANDARD_AREAS,
    STANDARDS_ROOT,
    TASK_ROOT,
    TASK_STATES,
)
from .models import FactoryConfig
from .dependencies import dependency_problems
from .tooling import tooling_problems
from .verification import verification_problems


@dataclass
class ValidationReport:
    project_dir: Path
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.errors


def has_factory_submodule(project_dir: Path) -> bool:
    gitmodules = project_dir / ".gitmodules"
    if not gitmodules.exists():
        return False
    content = gitmodules.read_text(encoding="utf-8")
    return "path = .factory" in content or "path=.factory" in content


def inspect_project(project_dir: Path) -> ValidationReport:
    report = ValidationReport(project_dir)
    for path in REQUIRED_PROJECT_PATHS:
        if not (project_dir / path).exists():
            report.errors.append(f"missing required path: {path}")

    if not (project_dir / ".factory" / "AGENTS.md").exists() and has_factory_submodule(project_dir):
        report.errors.append(
            "factory submodule appears uninitialized; run `git submodule update --init .factory`"
        )

    for state in TASK_STATES:
        if not (project_dir / TASK_ROOT / state).is_dir():
            report.errors.append(f"missing task state directory: {TASK_ROOT}/{state}")
    for area in STANDARD_AREAS:
        if not (project_dir / STANDARDS_ROOT / f"{area}.md").exists():
            report.errors.append(f"missing standard: {STANDARDS_ROOT}/{area}.md")

    config_path = project_dir / FACTORY_CONFIG_PATH
    if config_path.exists():
        try:
            config = FactoryConfig.from_yaml(config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            report.errors.append(f"invalid factory config: {exc}")
        else:
            report.warnings.extend(config.ignored_setting_warnings())
            if "claude-code" in config.enabled_tools:
                bridge = project_dir / ".claude" / "CLAUDE.md"
                if not bridge.exists():
                    report.errors.append("Claude Code is enabled but .claude/CLAUDE.md is missing")
                elif "@../AGENTS.md" not in bridge.read_text(encoding="utf-8"):
                    report.errors.append("Claude Code bridge must import @../AGENTS.md")

    done_root = project_dir / TASK_ROOT / "done"
    if done_root.is_dir():
        for task_path in sorted(done_root.glob("*.md")):
            content = task_path.read_text(encoding="utf-8")
            if "Review" not in content and "REV-" not in content:
                report.errors.append(f"done task may be missing review reference: {task_path.name}")
            if "QA" not in content and "QA-" not in content:
                report.errors.append(f"done task may be missing QA reference: {task_path.name}")

    incomplete = project_dir / ".factory-state" / "import" / "INCOMPLETE"
    if incomplete.exists():
        report.errors.append(
            "import is incomplete; merge or resolve instruction proposals before running workflows"
        )

    clarification_errors, clarification_warnings = clarification_problems(project_dir)
    report.errors.extend(clarification_errors)
    report.warnings.extend(clarification_warnings)
    tooling_errors, tooling_warnings = tooling_problems(project_dir)
    report.errors.extend(tooling_errors)
    report.warnings.extend(tooling_warnings)
    dependency_errors, dependency_warnings = dependency_problems(project_dir)
    report.errors.extend(dependency_errors)
    report.warnings.extend(dependency_warnings)
    verification_errors, verification_warnings = verification_problems(project_dir)
    report.errors.extend(verification_errors)
    report.warnings.extend(verification_warnings)
    from .readiness import readiness_problems

    ready_errors, ready_warnings = readiness_problems(project_dir)
    report.errors.extend(ready_errors)
    report.warnings.extend(ready_warnings)
    return report


def validate_project(project_dir: Path) -> int:
    report = inspect_project(project_dir)
    if report.errors:
        print("Project validation failed:")
        for problem in report.errors:
            print(f"  - {problem}")
    else:
        print(f"Project validation passed: {project_dir}")
    if report.warnings:
        print("Warnings:")
        for warning in report.warnings:
            print(f"  - {warning}")
    return 0 if report.passed else 1
