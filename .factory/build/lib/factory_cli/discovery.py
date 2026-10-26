from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


@dataclass
class ProjectScan:
    manifests: List[str] = field(default_factory=list)
    source_directories: List[str] = field(default_factory=list)
    test_directories: List[str] = field(default_factory=list)
    instruction_files: List[str] = field(default_factory=list)
    commands: Dict[str, str] = field(default_factory=dict)
    integration_branch: str = "develop"


MANIFEST_NAMES = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "go.mod",
    "Cargo.toml",
    "pubspec.yaml",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Makefile",
)


def scan_project(project_dir: Path) -> ProjectScan:
    scan = ProjectScan(integration_branch=detect_integration_branch(project_dir))
    candidates = []
    for name in MANIFEST_NAMES:
        candidates.append(project_dir / name)
        candidates.extend(project_dir.glob(f"*/{name}"))
    candidates.extend(project_dir.glob("*.csproj"))
    candidates.extend(project_dir.glob("*/*.csproj"))
    for path in sorted(set(candidates)):
        if path.is_file():
            scan.manifests.append(str(path.relative_to(project_dir)))

    for name in ("src", "app", "lib", "packages", "services", "apps"):
        path = project_dir / name
        if path.is_dir():
            scan.source_directories.append(name)
    for name in ("test", "tests", "integration_test", "e2e"):
        path = project_dir / name
        if path.is_dir():
            scan.test_directories.append(name)
    for name in ("AGENTS.md", "CLAUDE.md", ".claude/CLAUDE.md", ".cursorrules"):
        if (project_dir / name).is_file():
            scan.instruction_files.append(name)
    cursor_rules = project_dir / ".cursor" / "rules"
    if cursor_rules.is_dir():
        scan.instruction_files.append(".cursor/rules/")

    scan.commands.update(detect_commands(project_dir, scan.manifests))
    return scan


def detect_integration_branch(project_dir: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_dir,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "develop"
    current_branch = completed.stdout.strip()
    try:
        branches_result = subprocess.run(
            ["git", "branch", "--format=%(refname:short)"],
            cwd=project_dir,
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired):
        return current_branch or "develop"
    branches = set(branches_result.stdout.splitlines())
    for candidate in ("develop", "main", "master"):
        if candidate in branches:
            return candidate
    return current_branch or "develop"


def detect_commands(project_dir: Path, manifests: List[str]) -> Dict[str, str]:
    commands: Dict[str, str] = {}
    manifest_names = {Path(path).name for path in manifests}
    package_path = project_dir / "package.json"
    if package_path.is_file():
        try:
            package = json.loads(package_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            package = {}
        scripts = package.get("scripts", {}) if isinstance(package, dict) else {}
        if (project_dir / "pnpm-lock.yaml").exists():
            runner, install = "pnpm", "pnpm install"
        elif (project_dir / "yarn.lock").exists():
            runner, install = "yarn", "yarn install"
        else:
            runner, install = "npm run", "npm install"
        commands["install"] = install
        for command_name, script_names in {
            "run": ("dev", "start"),
            "test": ("test",),
            "build": ("build",),
            "lint": ("lint",),
            "typecheck": ("typecheck", "type-check"),
            "format": ("format",),
        }.items():
            selected = next((name for name in script_names if name in scripts), None)
            if selected:
                commands[command_name] = (
                    f"yarn {selected}" if runner == "yarn" else f"{runner} {selected}"
                )
    if "pubspec.yaml" in manifest_names:
        commands.update(
            {
                "install": "flutter pub get",
                "run": "flutter run",
                "test": "flutter test",
                "build": "flutter build",
                "lint": "flutter analyze",
                "format": "dart format --output=none --set-exit-if-changed lib test",
            }
        )
    if "go.mod" in manifest_names:
        commands.update(
            {"test": "go test ./...", "build": "go build ./...", "format": "gofmt -w ."}
        )
    if "Cargo.toml" in manifest_names:
        commands.update(
            {
                "test": "cargo test",
                "build": "cargo build",
                "lint": "cargo clippy",
                "format": "cargo fmt",
            }
        )
    if "pom.xml" in manifest_names:
        wrapper = "./mvnw" if (project_dir / "mvnw").is_file() else "mvn"
        commands.update(
            {
                "install": f"{wrapper} dependency:go-offline",
                "run": f"{wrapper} spring-boot:run",
                "test": f"{wrapper} test",
                "build": f"{wrapper} verify",
            }
        )
    if any(name.endswith(".csproj") for name in manifest_names):
        commands.update(
            {
                "install": "dotnet restore",
                "run": "dotnet run",
                "test": "dotnet test",
                "build": "dotnet build --no-restore",
                "format": "dotnet format",
            }
        )
    pyproject = project_dir / "pyproject.toml"
    if pyproject.is_file():
        content = pyproject.read_text(encoding="utf-8")
        if "pytest" in content or (project_dir / "tests").is_dir():
            commands.setdefault("test", "pytest")
        if re.search(r"\b(?:ruff)\b", content):
            commands.setdefault("lint", "ruff check .")
            commands.setdefault("format", "ruff format .")
        if re.search(r"\b(?:mypy|pyright)\b", content):
            commands.setdefault("typecheck", "mypy .")
    return commands


def render_import_assessment(project_name: str, scan: ProjectScan) -> str:
    def bullets(items: List[str]) -> str:
        return "\n".join(f"- `{item}`" for item in items) if items else "- None observed."

    command_lines = (
        "\n".join(f"- {name.title()}: `{command}`" for name, command in scan.commands.items())
        if scan.commands
        else "- No commands detected."
    )
    return f"""# Discovery: Import Assessment

## Project

- Name: {project_name}
- Integration branch: `{scan.integration_branch}`

## Observed Manifests

{bullets(scan.manifests)}

## Observed Source Directories

{bullets(scan.source_directories)}

## Observed Test Directories

{bullets(scan.test_directories)}

## Existing AI Instructions

{bullets(scan.instruction_files)}

## Commands Inferred From Repository Evidence

{command_lines}

## Constraints

- Inferred commands must be validated before they become project standards.
- Manifest presence is evidence of a tool or ecosystem, not approval of an architecture.
"""
