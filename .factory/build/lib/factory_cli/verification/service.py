from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import yaml

from ..constants import VERIFICATION_METADATA_PATH, VERIFICATION_ROOT
from ..project import atomic_write
from .models import VerificationCheck, VerificationPlan, VerificationResult


VERIFICATION_SCHEMA_VERSION = 1
VERIFICATION_TIMEOUT_SECONDS = 300
PROFILES = {"quick", "full"}
CHECK_KINDS = {"check", "test", "lint", "typecheck", "build"}
QUICK_KINDS = {"check", "test", "lint", "typecheck"}
IGNORED_DIRECTORIES = {
    ".dart_tool",
    ".factory",
    ".factory-state",
    ".git",
    ".next",
    ".svelte-kit",
    ".venv",
    "bin",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "obj",
    "target",
}
INPUT_NAMES = {
    "angular.json",
    "go.mod",
    "go.sum",
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
    "pom.xml",
    "pubspec.yaml",
    "pubspec.lock",
    "pyproject.toml",
    "requirements.txt",
}
INPUT_SUFFIXES = {
    ".cs",
    ".csproj",
    ".dart",
    ".go",
    ".html",
    ".java",
    ".js",
    ".jsx",
    ".json",
    ".kt",
    ".py",
    ".svelte",
    ".ts",
    ".tsx",
    ".vue",
}


class VerificationError(Exception):
    """Blocking verification planning, execution, or validation problem."""


def create_verification_plan(
    project_dir: Path,
    *,
    profile: str = "quick",
    selected_kinds: Sequence[str] = (),
) -> VerificationPlan:
    if not project_dir.is_dir():
        raise VerificationError(f"Project directory does not exist: {project_dir}")
    if profile not in PROFILES:
        raise VerificationError(f"Unsupported verification profile: {profile}")
    invalid = sorted(set(selected_kinds) - CHECK_KINDS)
    if invalid:
        raise VerificationError(f"Unsupported verification checks: {', '.join(invalid)}")
    inputs = _verification_inputs(project_dir)
    plan = VerificationPlan(
        project_dir=str(project_dir),
        source_sha256=_input_sha256(project_dir, inputs),
        profile=profile,
    )
    requested = set(selected_kinds) if selected_kinds else None

    _discover_node_checks(project_dir, plan)
    _discover_python_checks(project_dir, plan)
    _discover_flutter_checks(project_dir, plan)
    _discover_maven_checks(project_dir, plan)
    _discover_dotnet_checks(project_dir, plan)
    _discover_go_checks(project_dir, plan)

    allowed = CHECK_KINDS if profile == "full" else QUICK_KINDS
    plan.checks = [
        check
        for check in plan.checks
        if check.kind in allowed and (requested is None or check.kind in requested)
    ]
    plan.checks.sort(key=lambda item: (item.working_dir, item.kind, item.check_id))
    if not plan.checks and not plan.errors:
        plan.errors.append("no supported verification checks were discovered")
    return plan


def _discover_node_checks(project_dir: Path, plan: VerificationPlan) -> None:
    scaffold_outputs = _scaffold_output_adapters(project_dir)
    for manifest in _find_name(project_dir, "package.json"):
        relative = manifest.relative_to(project_dir).as_posix()
        working_dir = manifest.parent.relative_to(project_dir).as_posix() or "."
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
            scripts = data.get("scripts", {}) if isinstance(data, dict) else {}
            if not isinstance(scripts, dict):
                raise ValueError("scripts must be an object")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            plan.errors.append(f"invalid Node manifest {relative}: {exc}")
            continue
        manager, error = _node_manager(
            manifest.parent,
            data,
            scaffold_outputs.get(relative),
        )
        if error:
            plan.errors.append(f"invalid Node manager evidence for {relative}: {error}")
            continue
        if manager is None:
            plan.errors.append(
                f"package manager is unknown for {relative}; add packageManager or a lockfile"
            )
            continue
        executable = shutil.which(manager)
        if executable is None:
            plan.errors.append(f"{manager} was not found on PATH for {relative}")
            continue
        for kind, candidates in (
            ("test", ("test",)),
            ("lint", ("lint",)),
            ("typecheck", ("typecheck", "type-check")),
            ("build", ("build",)),
        ):
            script = next((name for name in candidates if name in scripts), None)
            if script is None:
                continue
            argv = (
                [executable, script]
                if manager == "yarn"
                else [executable, "run", script]
            )
            plan.checks.append(
                VerificationCheck(
                    check_id=f"node:{working_dir}:{kind}",
                    kind=kind,
                    working_dir=working_dir,
                    argv=argv,
                    source=relative,
                )
            )


def _discover_python_checks(project_dir: Path, plan: VerificationPlan) -> None:
    for manifest in _find_name(project_dir, "pyproject.toml"):
        relative = manifest.relative_to(project_dir).as_posix()
        directory = manifest.parent
        working_dir = directory.relative_to(project_dir).as_posix() or "."
        python_relative = (
            ".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python"
        )
        python = directory / python_relative
        content = manifest.read_text(encoding="utf-8")
        candidates: List[Tuple[str, List[str]]] = []
        manage = directory / "manage.py"
        if manage.is_file():
            candidates.extend(
                (
                    ("check", [python_relative, "manage.py", "check"]),
                    ("test", [python_relative, "manage.py", "test"]),
                )
            )
        elif "pytest" in content:
            candidates.append(("test", [python_relative, "-m", "pytest"]))
        elif (directory / "tests").is_dir():
            candidates.append(
                (
                    "test",
                    [
                        python_relative,
                        "-m",
                        "unittest",
                        "discover",
                        "-s",
                        "tests",
                        "-v",
                    ],
                )
            )
        if "ruff" in content:
            candidates.append(("lint", [python_relative, "-m", "ruff", "check", "."]))
        if "mypy" in content:
            candidates.append(("typecheck", [python_relative, "-m", "mypy", "."]))
        elif "pyright" in content:
            candidates.append(("typecheck", [python_relative, "-m", "pyright"]))
        if candidates and not python.is_file():
            plan.errors.append(
                f"Python verification environment is missing for {relative}; run factory deps apply"
            )
            continue
        for kind, argv in candidates:
            plan.checks.append(
                VerificationCheck(
                    check_id=f"python:{working_dir}:{kind}",
                    kind=kind,
                    working_dir=working_dir,
                    argv=argv,
                    source=relative,
                )
            )


def _discover_flutter_checks(project_dir: Path, plan: VerificationPlan) -> None:
    for manifest in _find_name(project_dir, "pubspec.yaml"):
        relative = manifest.relative_to(project_dir).as_posix()
        working_dir = manifest.parent.relative_to(project_dir).as_posix() or "."
        executable = shutil.which("flutter")
        if executable is None:
            plan.errors.append(f"flutter was not found on PATH for {relative}")
            continue
        for kind, arguments in (
            ("lint", ["analyze"]),
            ("test", ["test"]),
        ):
            plan.checks.append(
                VerificationCheck(
                    check_id=f"flutter:{working_dir}:{kind}",
                    kind=kind,
                    working_dir=working_dir,
                    argv=[executable, *arguments],
                    source=relative,
                )
            )


def _discover_maven_checks(project_dir: Path, plan: VerificationPlan) -> None:
    for manifest in _find_name(project_dir, "pom.xml"):
        relative = manifest.relative_to(project_dir).as_posix()
        working_dir = manifest.parent.relative_to(project_dir).as_posix() or "."
        executable = _maven_executable(manifest.parent)
        if executable is None:
            plan.errors.append(f"Maven wrapper or mvn was not found for {relative}")
            continue
        plan.checks.extend(
            (
                VerificationCheck(
                    f"maven:{working_dir}:test",
                    "test",
                    working_dir,
                    [executable, "--batch-mode", "--no-transfer-progress", "test"],
                    relative,
                ),
                VerificationCheck(
                    f"maven:{working_dir}:build",
                    "build",
                    working_dir,
                    [
                        executable,
                        "--batch-mode",
                        "--no-transfer-progress",
                        "package",
                        "-DskipTests",
                    ],
                    relative,
                ),
            )
        )


def _discover_dotnet_checks(project_dir: Path, plan: VerificationPlan) -> None:
    manifests = list(_find_suffix(project_dir, ".csproj"))
    if not manifests:
        return
    executable = shutil.which("dotnet")
    if executable is None:
        plan.errors.append("dotnet was not found on PATH for .NET verification")
        return
    for manifest in manifests:
        relative = manifest.relative_to(project_dir).as_posix()
        working_dir = manifest.parent.relative_to(project_dir).as_posix() or "."
        plan.checks.extend(
            (
                VerificationCheck(
                    f"dotnet:{working_dir}:test",
                    "test",
                    working_dir,
                    [executable, "test", manifest.name, "--no-restore"],
                    relative,
                ),
                VerificationCheck(
                    f"dotnet:{working_dir}:build",
                    "build",
                    working_dir,
                    [executable, "build", manifest.name, "--no-restore"],
                    relative,
                ),
            )
        )


def _discover_go_checks(project_dir: Path, plan: VerificationPlan) -> None:
    for manifest in _find_name(project_dir, "go.mod"):
        relative = manifest.relative_to(project_dir).as_posix()
        working_dir = manifest.parent.relative_to(project_dir).as_posix() or "."
        executable = shutil.which("go")
        if executable is None:
            plan.errors.append(f"go was not found on PATH for {relative}")
            continue
        for kind, arguments in (
            ("lint", ["vet", "./..."]),
            ("test", ["test", "./..."]),
            ("build", ["build", "./..."]),
        ):
            plan.checks.append(
                VerificationCheck(
                    f"go:{working_dir}:{kind}",
                    kind,
                    working_dir,
                    [executable, *arguments],
                    relative,
                )
            )


def run_verification_plan(
    plan: VerificationPlan,
    *,
    timeout_seconds: int = VERIFICATION_TIMEOUT_SECONDS,
) -> List[VerificationResult]:
    if not plan.ready:
        raise VerificationError("Verification plan is not ready; resolve its errors first.")
    project_dir = Path(plan.project_dir)
    if _input_sha256(project_dir, _verification_inputs(project_dir)) != plan.source_sha256:
        raise VerificationError(
            "Project verification inputs changed after planning; create a new plan."
        )
    results: List[VerificationResult] = []
    for check in plan.checks:
        started = datetime.now(timezone.utc).isoformat()
        before = time.monotonic()
        try:
            completed = subprocess.run(
                check.argv,
                cwd=project_dir / check.working_dir,
                env=_verification_environment(),
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            output = (completed.stdout + completed.stderr).strip()
            results.append(
                VerificationResult(
                    check=check,
                    status="passed" if completed.returncode == 0 else "failed",
                    returncode=completed.returncode,
                    started_at=started,
                    duration_seconds=time.monotonic() - before,
                    output=output[-4000:],
                )
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            results.append(
                VerificationResult(
                    check=check,
                    status="failed",
                    returncode=None,
                    started_at=started,
                    duration_seconds=time.monotonic() - before,
                    error=str(exc),
                )
            )
    _write_verification_state(project_dir, plan, results)
    return results


def verification_problems(
    project_dir: Path,
    *,
    require_state: bool = False,
) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    root = project_dir / VERIFICATION_ROOT
    metadata_path = project_dir / VERIFICATION_METADATA_PATH
    if not root.exists():
        if require_state:
            errors.append("project verification has not been run")
        return errors, warnings
    if not metadata_path.is_file():
        errors.append(f"missing verification metadata: {VERIFICATION_METADATA_PATH}")
        return errors, warnings
    try:
        data = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict) or data.get("schema_version") != VERIFICATION_SCHEMA_VERSION:
            raise ValueError("unsupported verification metadata schema")
        if data.get("status") not in {"passed", "failed"}:
            raise ValueError("status must be passed or failed")
        inputs = data.get("inputs")
        if not isinstance(inputs, dict):
            raise ValueError("inputs must be a mapping")
        results = data.get("results")
        if not isinstance(results, list):
            raise ValueError("results must be a list")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(f"invalid verification metadata: {exc}")
        return errors, warnings
    if data.get("status") == "failed":
        errors.append("latest project verification failed")
    current = _hash_mapping(project_dir, _verification_inputs(project_dir))
    if current != inputs:
        warnings.append("project inputs changed after the latest verification run")
    for result in results:
        if not isinstance(result, dict) or result.get("status") not in {"passed", "failed"}:
            errors.append("invalid verification result metadata")
    return errors, warnings


def render_verification_review(plan: VerificationPlan) -> str:
    return "\n".join(
        (
            "# Project verification review",
            "",
            (
                "Factory will run only deterministic validation checks discovered "
                "from project manifests."
            ),
            (
                "No expected free-text command, formatter, migration, server, or "
                "deployment action is included."
            ),
            (
                "Build and test tools may create their normal project-local caches "
                "or output directories."
            ),
            "",
            "```text",
            plan.render(),
            "```",
        )
    )


def _write_verification_state(
    project_dir: Path,
    plan: VerificationPlan,
    results: List[VerificationResult],
) -> None:
    now = datetime.now(timezone.utc)
    status = "passed" if all(result.status == "passed" for result in results) else "failed"
    serialized = []
    for result in results:
        item = result.to_dict()
        output = result.output or result.error
        item["output_sha256"] = hashlib.sha256(output.encode("utf-8")).hexdigest()
        serialized.append(item)
    data = {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "run_id": now.strftime("%Y%m%dT%H%M%S%fZ"),
        "status": status,
        "profile": plan.profile,
        "updated_at": now.isoformat(),
        "source_sha256": plan.source_sha256,
        "inputs": _hash_mapping(project_dir, _verification_inputs(project_dir)),
        "results": serialized,
    }
    rendered = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
    atomic_write(project_dir / VERIFICATION_METADATA_PATH, rendered)
    atomic_write(
        project_dir / VERIFICATION_ROOT / "runs" / f"{data['run_id']}.yaml",
        rendered,
    )


def _walk_project_files(project_dir: Path) -> Iterator[Path]:
    for raw_root, directories, filenames in os.walk(project_dir, topdown=True):
        root = Path(raw_root)
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in IGNORED_DIRECTORIES
            and not (root / directory).is_symlink()
        )
        for filename in sorted(filenames):
            path = root / filename
            if path.is_file() and not path.is_symlink():
                yield path


def _find_name(project_dir: Path, filename: str) -> Iterable[Path]:
    return (path for path in _walk_project_files(project_dir) if path.name == filename)


def _find_suffix(project_dir: Path, suffix: str) -> Iterable[Path]:
    return (path for path in _walk_project_files(project_dir) if path.name.endswith(suffix))


def _verification_inputs(project_dir: Path) -> List[Path]:
    return [
        path
        for path in _walk_project_files(project_dir)
        if path.name in INPUT_NAMES or path.suffix in INPUT_SUFFIXES
    ]


def _hash_mapping(project_dir: Path, paths: List[Path]) -> Dict[str, str]:
    return {
        path.relative_to(project_dir).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def _input_sha256(project_dir: Path, paths: List[Path]) -> str:
    rendered = yaml.safe_dump(
        _hash_mapping(project_dir, paths), sort_keys=True, allow_unicode=True
    )
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _verification_environment() -> Dict[str, str]:
    environment = os.environ.copy()
    environment.update({"CI": "1", "NO_COLOR": "1"})
    return environment


def _node_manager(
    directory: Path,
    data: Dict[str, object],
    scaffold_adapter_id: Optional[str],
) -> Tuple[Optional[str], Optional[str]]:
    lock_managers = [
        manager
        for manager, present in (
            ("npm", (directory / "package-lock.json").exists()),
            ("pnpm", (directory / "pnpm-lock.yaml").exists()),
            ("yarn", (directory / "yarn.lock").exists()),
            ("bun", (directory / "bun.lock").exists() or (directory / "bun.lockb").exists()),
        )
        if present
    ]
    if len(lock_managers) > 1:
        return None, "conflicting lockfiles select " + ", ".join(lock_managers)
    package_manager = data.get("packageManager")
    declared = None
    if isinstance(package_manager, str):
        candidate = package_manager.split("@", 1)[0]
        if candidate in {"npm", "pnpm", "yarn", "bun"}:
            declared = candidate
    if lock_managers:
        locked = lock_managers[0]
        if declared and declared != locked:
            return None, f"{locked} lockfile conflicts with packageManager {declared}"
        return locked, None
    if declared:
        return declared, None
    if scaffold_adapter_id in {"vite", "nextjs", "sveltekit", "angular", "nestjs"}:
        return "npm", None
    return None, None


def _scaffold_output_adapters(project_dir: Path) -> Dict[str, str]:
    metadata = project_dir / ".factory-state" / "scaffolding" / "generated.yaml"
    if not metadata.is_file():
        return {}
    try:
        data = yaml.safe_load(metadata.read_text(encoding="utf-8")) or {}
        outputs = data.get("outputs", {})
        if not isinstance(outputs, dict):
            return {}
        return {
            path: output["adapter"]
            for path, output in outputs.items()
            if isinstance(path, str)
            and isinstance(output, dict)
            and isinstance(output.get("adapter"), str)
        }
    except (OSError, yaml.YAMLError, AttributeError):
        return {}


def _maven_executable(directory: Path) -> Optional[str]:
    wrapper_name = "mvnw.cmd" if os.name == "nt" else "mvnw"
    if (directory / wrapper_name).is_file():
        return wrapper_name if os.name == "nt" else f"./{wrapper_name}"
    return shutil.which("mvn")
