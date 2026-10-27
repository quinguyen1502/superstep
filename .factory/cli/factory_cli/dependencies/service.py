from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

import yaml

from ..constants import DEPENDENCY_METADATA_PATH, DEPENDENCY_ROOT
from ..project import atomic_write
from .models import DependencyCommand, DependencyPlan, portable_argv


DEPENDENCY_SCHEMA_VERSION = 1
DEPENDENCY_TIMEOUT_SECONDS = 900
INTEGRITY_TIMEOUT_SECONDS = 60
INPUT_FILENAMES = {
    "package.json",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "bun.lock",
    "bun.lockb",
    "pyproject.toml",
    "requirements.txt",
    "uv.lock",
    "pubspec.yaml",
    "pubspec.lock",
    "pom.xml",
    "go.mod",
    "go.sum",
    "packages.lock.json",
}
# Build output and tool caches: a manifest copied into them (such as a
# package.json under dist/) is not a project manifest.
IGNORED_PARTS = {
    ".factory",
    ".factory-state",
    ".git",
    ".next",
    ".svelte-kit",
    ".venv",
    "node_modules",
    ".dart_tool",
    "build",
    "coverage",
    "dist",
    "target",
    "obj",
}
NODE_ADAPTERS = {"vite", "nextjs", "sveltekit", "angular", "nestjs"}


class DependencyError(Exception):
    """Blocking dependency planning, execution, or validation problem."""


def create_dependency_plan(project_dir: Path) -> DependencyPlan:
    if not project_dir.is_dir():
        raise DependencyError(f"Project directory does not exist: {project_dir}")
    inputs = _dependency_inputs(project_dir)
    plan = DependencyPlan(
        project_dir=str(project_dir),
        source_sha256=_input_sha256(project_dir, inputs),
    )
    scaffold_outputs = _scaffold_output_adapters(project_dir)
    claimed_python_directories = set()

    for manifest in _find_files(project_dir, "package.json"):
        command, error = _node_command(project_dir, manifest, scaffold_outputs)
        if error:
            plan.errors.append(error)
        elif command is not None:
            plan.commands.append(command)

    for manifest in _find_files(project_dir, "pyproject.toml"):
        claimed_python_directories.add(manifest.parent)
        plan.commands.extend(_python_commands(project_dir, manifest, plan.errors))

    for manifest in _find_files(project_dir, "requirements.txt"):
        if manifest.parent in claimed_python_directories:
            continue
        plan.commands.extend(_requirements_commands(project_dir, manifest))

    for manifest in _find_files(project_dir, "pubspec.yaml"):
        relative = manifest.relative_to(project_dir).as_posix()
        executable = shutil.which("flutter")
        if executable is None:
            plan.errors.append(
                f"flutter was not found on PATH for {relative}; install the Flutter SDK"
            )
            continue
        working_dir = manifest.parent.relative_to(project_dir).as_posix() or "."
        plan.commands.append(
            DependencyCommand(
                target_id=f"flutter:{working_dir}",
                manager="flutter",
                working_dir=working_dir,
                argv=[executable, "pub", "get"],
                manifest=relative,
                expected_paths=[_join_relative(working_dir, ".dart_tool/package_config.json")],
            )
        )

    for manifest in _find_files(project_dir, "pom.xml"):
        command, error = _maven_command(project_dir, manifest)
        if error:
            plan.errors.append(error)
        elif command is not None:
            plan.commands.append(command)

    for manifest in _find_suffix(project_dir, ".csproj"):
        executable = shutil.which("dotnet")
        relative = manifest.relative_to(project_dir).as_posix()
        if executable is None:
            plan.errors.append(f"dotnet was not found on PATH for {relative}")
            continue
        working_dir = manifest.parent.relative_to(project_dir).as_posix() or "."
        plan.commands.append(
            DependencyCommand(
                target_id=f"dotnet:{working_dir}",
                manager="dotnet",
                working_dir=working_dir,
                argv=[executable, "restore", manifest.name],
                manifest=relative,
                expected_paths=[
                    _join_relative(working_dir, "obj/project.assets.json")
                ],
            )
        )

    for manifest in _find_files(project_dir, "go.mod"):
        executable = shutil.which("go")
        relative = manifest.relative_to(project_dir).as_posix()
        if executable is None:
            plan.errors.append(f"go was not found on PATH for {relative}")
            continue
        working_dir = manifest.parent.relative_to(project_dir).as_posix() or "."
        plan.commands.append(
            DependencyCommand(
                target_id=f"go:{working_dir}",
                manager="go",
                working_dir=working_dir,
                argv=[executable, "mod", "download"],
                manifest=relative,
            )
        )

    if not plan.commands and not plan.errors:
        plan.errors.append("no supported dependency manifests were found")
    return plan


def _find_files(project_dir: Path, filename: str) -> Iterable[Path]:
    for path in _walk_project_files(project_dir):
        if path.name == filename:
            yield path


def _find_suffix(project_dir: Path, suffix: str) -> Iterable[Path]:
    for path in _walk_project_files(project_dir):
        if path.name.endswith(suffix):
            yield path


def _maven_command(
    project_dir: Path,
    manifest: Path,
) -> Tuple[Optional[DependencyCommand], Optional[str]]:
    working_dir = manifest.parent.relative_to(project_dir).as_posix() or "."
    relative = manifest.relative_to(project_dir).as_posix()
    wrapper_name = "mvnw.cmd" if os.name == "nt" else "mvnw"
    wrapper = manifest.parent / wrapper_name
    if wrapper.is_file():
        executable = wrapper_name if os.name == "nt" else f"./{wrapper_name}"
    else:
        executable = shutil.which("mvn")
        if executable is None:
            return None, f"Maven wrapper or mvn was not found for {relative}"
    return (
        DependencyCommand(
            target_id=f"maven:{working_dir}",
            manager="maven",
            working_dir=working_dir,
            argv=[
                executable,
                "--batch-mode",
                "--no-transfer-progress",
                "dependency:go-offline",
            ],
            manifest=relative,
        ),
        None,
    )


def _walk_project_files(project_dir: Path) -> Iterator[Path]:
    for raw_root, directories, filenames in os.walk(project_dir, topdown=True):
        root = Path(raw_root)
        directories[:] = sorted(
            directory
            for directory in directories
            if directory not in IGNORED_PARTS
            and not (root / directory).is_symlink()
        )
        for filename in sorted(filenames):
            path = root / filename
            if path.is_file() and not path.is_symlink():
                yield path


def _node_command(
    project_dir: Path,
    manifest: Path,
    scaffold_outputs: Dict[str, str],
) -> Tuple[Optional[DependencyCommand], Optional[str]]:
    relative = manifest.relative_to(project_dir).as_posix()
    working_dir = manifest.parent.relative_to(project_dir).as_posix() or "."
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("package.json must contain an object")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return None, f"invalid Node manifest {relative}: {exc}"

    manager, manager_error = _node_manager(
        manifest.parent,
        data,
        scaffold_outputs.get(relative),
    )
    if manager_error:
        return None, f"invalid Node package-manager evidence for {relative}: {manager_error}"
    if manager is None:
        return None, (
            f"package manager is unknown for {relative}; add packageManager or a lockfile"
        )
    executable = shutil.which(manager)
    if executable is None:
        return None, f"{manager} was not found on PATH for {relative}"
    lockfiles = {
        "npm": manifest.parent / "package-lock.json",
        "pnpm": manifest.parent / "pnpm-lock.yaml",
        "yarn": manifest.parent / "yarn.lock",
        "bun": next(
            (
                path
                for path in (manifest.parent / "bun.lock", manifest.parent / "bun.lockb")
                if path.exists()
            ),
            manifest.parent / "bun.lock",
        ),
    }
    locked = lockfiles[manager].exists()
    argv = {
        "npm": (
            [executable, "ci", "--include=dev"]
            if locked
            else [executable, "install", "--include=dev"]
        ),
        "pnpm": [executable, "install", "--frozen-lockfile"] if locked else [executable, "install"],
        "yarn": [executable, "install", "--frozen-lockfile"] if locked else [executable, "install"],
        "bun": [executable, "install", "--frozen-lockfile"] if locked else [executable, "install"],
    }[manager]
    has_packages = any(
        isinstance(data.get(key), dict) and bool(data[key])
        for key in ("dependencies", "devDependencies", "optionalDependencies")
    )
    return (
        DependencyCommand(
            target_id=f"node:{working_dir}",
            manager=manager,
            working_dir=working_dir,
            argv=argv,
            manifest=relative,
            expected_paths=(
                [_join_relative(working_dir, "node_modules")]
                if manager != "yarn" and has_packages
                else []
            ),
            integrity_argv=(
                [executable, "ls", "--depth=0", "--include=dev"]
                if manager == "npm"
                else []
            ),
        ),
        None,
    )


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
            (
                "bun",
                (directory / "bun.lock").exists()
                or (directory / "bun.lockb").exists(),
            ),
        )
        if present
    ]
    if len(lock_managers) > 1:
        return None, "conflicting lockfiles select " + ", ".join(lock_managers)
    package_manager = data.get("packageManager")
    declared_manager = None
    if isinstance(package_manager, str):
        manager = package_manager.split("@", 1)[0]
        if manager in {"npm", "pnpm", "yarn", "bun"}:
            declared_manager = manager
    if lock_managers:
        locked_manager = lock_managers[0]
        if declared_manager is not None and declared_manager != locked_manager:
            return None, (
                f"{locked_manager} lockfile conflicts with packageManager "
                f"{declared_manager}"
            )
        return locked_manager, None
    if declared_manager is not None:
        return declared_manager, None
    if scaffold_adapter_id in NODE_ADAPTERS:
        return "npm", None
    return None, None


def _python_commands(
    project_dir: Path,
    manifest: Path,
    errors: List[str],
) -> List[DependencyCommand]:
    working_dir = manifest.parent.relative_to(project_dir).as_posix() or "."
    relative = manifest.relative_to(project_dir).as_posix()
    uv_lock = manifest.parent / "uv.lock"
    if uv_lock.is_file():
        executable = shutil.which("uv")
        if executable is None:
            errors.append(f"uv was not found on PATH for {relative}")
            return []
        return [
            DependencyCommand(
                target_id=f"python:{working_dir}",
                manager="uv",
                working_dir=working_dir,
                argv=[executable, "sync", "--locked"],
                manifest=relative,
                expected_paths=[_join_relative(working_dir, ".venv")],
            )
        ]
    install_target = "."
    try:
        content = manifest.read_text(encoding="utf-8")
    except OSError:
        content = ""
    optional = re.search(
        r"(?ms)^\[project\.optional-dependencies\]\s*$\n(.*?)(?=^\[|\Z)",
        content,
    )
    if optional and re.search(r"(?m)^test\s*=", optional.group(1)):
        install_target = ".[test]"
    return _venv_and_pip_commands(
        project_dir, manifest, ["-e", install_target]
    )


def _requirements_commands(
    project_dir: Path,
    manifest: Path,
) -> List[DependencyCommand]:
    return _venv_and_pip_commands(project_dir, manifest, ["-r", manifest.name])


def _venv_and_pip_commands(
    project_dir: Path,
    manifest: Path,
    install_args: List[str],
) -> List[DependencyCommand]:
    working_dir = manifest.parent.relative_to(project_dir).as_posix() or "."
    relative = manifest.relative_to(project_dir).as_posix()
    venv = manifest.parent / ".venv"
    venv_python_relative = ".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python"
    commands: List[DependencyCommand] = []
    if not venv.exists():
        commands.append(
            DependencyCommand(
                target_id=f"python-venv:{working_dir}",
                manager="venv",
                working_dir=working_dir,
                argv=[sys.executable, "-m", "venv", ".venv"],
                manifest=relative,
                requires_network=False,
                expected_paths=[_join_relative(working_dir, venv_python_relative)],
            )
        )
    elif not (manifest.parent / venv_python_relative).is_file():
        raise DependencyError(f"existing Python environment is invalid: {venv}")
    commands.append(
        DependencyCommand(
            target_id=f"python:{working_dir}",
            manager="pip",
            working_dir=working_dir,
            argv=[venv_python_relative, "-m", "pip", "install"] + install_args,
            manifest=relative,
            expected_paths=[_join_relative(working_dir, venv_python_relative)],
        )
    )
    return commands


def apply_dependency_plan(
    plan: DependencyPlan,
    *,
    allow_network: bool = False,
    timeout_seconds: int = DEPENDENCY_TIMEOUT_SECONDS,
) -> None:
    if not plan.ready:
        raise DependencyError("Dependency plan is not ready; resolve its errors first.")
    if plan.requires_network and not allow_network:
        raise DependencyError(
            "Dependency installation requires network approval; rerun with --allow-network"
        )
    project_dir = Path(plan.project_dir)
    if _input_sha256(project_dir, _dependency_inputs(project_dir)) != plan.source_sha256:
        raise DependencyError("Dependency manifests changed after planning; create a new plan.")

    results: List[Dict[str, object]] = []
    failure: Optional[str] = None
    for command in plan.commands:
        started = datetime.now(timezone.utc).isoformat()
        try:
            completed = subprocess.run(
                command.argv,
                cwd=project_dir / command.working_dir,
                env=_dependency_environment(),
                text=True,
                capture_output=True,
                timeout=timeout_seconds,
                check=False,
            )
            result = {
                **command.to_dict(),
                "started_at": started,
                "returncode": completed.returncode,
                "status": "observed" if completed.returncode == 0 else "failed",
            }
            results.append(result)
            if completed.returncode:
                detail = (completed.stderr or completed.stdout or "unknown error").strip()
                failure = (
                    f"{command.target_id} failed with status {completed.returncode}: "
                    f"{detail[-2000:]}"
                )
                break
            if command.integrity_argv:
                integrity = subprocess.run(
                    command.integrity_argv,
                    cwd=project_dir / command.working_dir,
                    env=_dependency_environment(),
                    text=True,
                    capture_output=True,
                    timeout=timeout_seconds,
                    check=False,
                )
                result["integrity"] = {
                    "argv": portable_argv(command.integrity_argv),
                    "returncode": integrity.returncode,
                    "status": (
                        "observed" if integrity.returncode == 0 else "failed"
                    ),
                }
                if integrity.returncode:
                    detail = (
                        integrity.stderr or integrity.stdout or "unknown error"
                    ).strip()
                    failure = (
                        f"{command.target_id} integrity check failed with status "
                        f"{integrity.returncode}: {detail[-2000:]}"
                    )
                    break
                package_errors = _node_package_problems(
                    project_dir,
                    command.working_dir,
                    command.manifest,
                )
                if package_errors:
                    failure = (
                        f"{command.target_id} integrity check failed: "
                        + "; ".join(package_errors)
                    )
                    result["integrity"]["status"] = "failed"
                    result["integrity"]["errors"] = package_errors
                    break
        except (OSError, subprocess.TimeoutExpired) as exc:
            failure = f"{command.target_id} failed: {exc}"
            results.append(
                {
                    **command.to_dict(),
                    "started_at": started,
                    "returncode": None,
                    "status": "failed",
                    "error": str(exc),
                }
            )
            break

    if failure is None:
        missing = _missing_expected_paths(project_dir, plan.commands)
        if missing:
            failure = "dependency commands completed but expected paths are missing: " + ", ".join(missing)

    _write_dependency_state(project_dir, plan, results, failure)
    if failure is not None:
        raise DependencyError(failure)


def _dependency_environment() -> Dict[str, str]:
    environment = os.environ.copy()
    environment.update({"CI": "1", "NO_COLOR": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1"})
    return environment


def _missing_expected_paths(
    project_dir: Path,
    commands: List[DependencyCommand],
) -> List[str]:
    expected = {
        path
        for command in commands
        for path in command.expected_paths
    }
    return sorted(path for path in expected if not (project_dir / path).exists())


def _write_dependency_state(
    project_dir: Path,
    plan: DependencyPlan,
    results: List[Dict[str, object]],
    failure: Optional[str],
) -> None:
    data = {
        "schema_version": DEPENDENCY_SCHEMA_VERSION,
        "status": "incomplete" if failure else "installed",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "source_sha256": plan.source_sha256,
        "inputs": _hash_mapping(project_dir, _dependency_inputs(project_dir)),
        "commands": results,
        "failure": failure,
    }
    atomic_write(
        project_dir / DEPENDENCY_METADATA_PATH,
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
    )
    incomplete = project_dir / DEPENDENCY_ROOT / "INCOMPLETE"
    if failure:
        atomic_write(incomplete, failure + "\n")
    elif incomplete.exists():
        incomplete.unlink()


def dependency_problems(
    project_dir: Path,
    *,
    require_state: bool = False,
    check_integrity: bool = False,
) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    root = project_dir / DEPENDENCY_ROOT
    metadata_path = project_dir / DEPENDENCY_METADATA_PATH
    incomplete = root / "INCOMPLETE"
    if not root.exists():
        if require_state:
            errors.append("dependency installation has not been applied")
        return errors, warnings
    if incomplete.exists():
        errors.append(f"dependency installation is incomplete; review {DEPENDENCY_ROOT}/INCOMPLETE")
    if not metadata_path.is_file():
        errors.append(f"missing dependency metadata: {DEPENDENCY_METADATA_PATH}")
        return errors, warnings
    try:
        data = yaml.safe_load(metadata_path.read_text(encoding="utf-8")) or {}
        if not isinstance(data, dict) or data.get("schema_version") != DEPENDENCY_SCHEMA_VERSION:
            raise ValueError("unsupported dependency metadata schema")
        if data.get("status") not in {"installed", "incomplete"}:
            raise ValueError("status must be installed or incomplete")
        inputs = data.get("inputs")
        if not isinstance(inputs, dict):
            raise ValueError("inputs must be a mapping")
        commands = data.get("commands")
        if not isinstance(commands, list):
            raise ValueError("commands must be a list")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(f"invalid dependency metadata: {exc}")
        return errors, warnings

    current = _hash_mapping(project_dir, _dependency_inputs(project_dir))
    if current != inputs:
        warnings.append("dependency manifests or lockfiles changed after installation")
    if data.get("status") == "incomplete" and not incomplete.exists():
        errors.append("dependency metadata is incomplete but INCOMPLETE marker is missing")
    for raw_command in commands:
        if not isinstance(raw_command, dict):
            errors.append("invalid dependency command metadata")
            continue
        if raw_command.get("status") != "observed":
            if data.get("status") == "installed":
                errors.append("installed dependency metadata contains an unobserved command")
            continue
        expected_paths = raw_command.get("expected_paths", [])
        if not isinstance(expected_paths, list):
            errors.append("invalid dependency expected paths metadata")
            continue
        for path in expected_paths:
            if not _is_safe_relative_path(path):
                errors.append(f"invalid dependency environment output path: {path}")
            elif not (project_dir / path).exists():
                errors.append(f"missing dependency environment output: {path}")
        if raw_command.get("manager") == "npm":
            working_dir = raw_command.get("working_dir")
            manifest = raw_command.get("manifest")
            if not _is_safe_relative_path(working_dir):
                errors.append("invalid npm dependency working directory")
                continue
            if not _is_safe_relative_path(manifest):
                errors.append("invalid npm dependency manifest path")
                continue
            if current.get(manifest) != inputs.get(manifest):
                continue
            errors.extend(
                _node_package_problems(project_dir, working_dir, manifest)
            )
            integrity = raw_command.get("integrity")
            if integrity is None:
                warnings.append(
                    f"npm installation for {working_dir} lacks integrity evidence; "
                    "rerun factory deps apply"
                )
            elif not isinstance(integrity, dict) or integrity.get("status") != "observed":
                errors.append("npm dependency integrity check was not successful")
            if check_integrity:
                integrity_problem = _npm_integrity_problem(
                    project_dir,
                    working_dir,
                )
                if integrity_problem:
                    errors.append(integrity_problem)
    return errors, warnings


def _node_package_problems(
    project_dir: Path,
    working_dir: str,
    manifest: str,
) -> List[str]:
    problems: List[str] = []
    manifest_path = project_dir / manifest
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("package.json must contain an object")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return [f"cannot validate npm packages from {manifest}: {exc}"]

    node_modules = project_dir / working_dir / "node_modules"
    for group in ("dependencies", "devDependencies"):
        declared = data.get(group, {})
        if declared is None:
            continue
        if not isinstance(declared, dict):
            problems.append(f"{manifest} has invalid {group}")
            continue
        for package_name in sorted(declared):
            package_path = _node_package_path(node_modules, package_name)
            if package_path is None:
                problems.append(
                    f"{manifest} has invalid package name in {group}: {package_name}"
                )
            elif not package_path.exists():
                problems.append(
                    f"missing installed {group} package: {package_name} ({working_dir})"
                )
    return problems


def _node_package_path(node_modules: Path, package_name: object) -> Optional[Path]:
    if not isinstance(package_name, str) or not package_name or "\\" in package_name:
        return None
    relative = PurePosixPath(package_name)
    if relative.is_absolute() or any(part in {"", ".", ".."} for part in relative.parts):
        return None
    if len(relative.parts) > 2 or (
        len(relative.parts) == 2 and not relative.parts[0].startswith("@")
    ):
        return None
    return node_modules.joinpath(*relative.parts)


def _npm_integrity_problem(project_dir: Path, working_dir: str) -> Optional[str]:
    executable = shutil.which("npm")
    if executable is None:
        return f"cannot validate npm dependencies for {working_dir}: npm was not found on PATH"
    try:
        completed = subprocess.run(
            [executable, "ls", "--depth=0", "--include=dev"],
            cwd=project_dir / working_dir,
            env=_dependency_environment(),
            text=True,
            capture_output=True,
            timeout=INTEGRITY_TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"npm dependency integrity check failed for {working_dir}: {exc}"
    if completed.returncode == 0:
        return None
    detail = (completed.stderr or completed.stdout or "unknown error").strip()
    return (
        f"npm dependency integrity check failed for {working_dir} with status "
        f"{completed.returncode}: {detail[-2000:]}"
    )


def render_dependency_review(plan: DependencyPlan) -> str:
    return "\n".join(
        (
            "# Dependency installation review",
            "",
            "Source scaffolding is already published. Dependency installation may use "
            "network access and modifies only project-local environments, caches, and lockfiles.",
            "",
            "```text",
            plan.render(),
            "```",
            "",
            "A failed install keeps source intact and records an incomplete dependency state for retry.",
        )
    )


def _dependency_inputs(project_dir: Path) -> List[Path]:
    return [
        path
        for path in _walk_project_files(project_dir)
        if path.name in INPUT_FILENAMES or path.name.endswith(".csproj")
    ]


def _hash_mapping(project_dir: Path, paths: List[Path]) -> Dict[str, str]:
    return {
        path.relative_to(project_dir).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def _input_sha256(project_dir: Path, paths: List[Path]) -> str:
    mapping = _hash_mapping(project_dir, paths)
    rendered = yaml.safe_dump(mapping, sort_keys=True, allow_unicode=True)
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


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


def _join_relative(directory: str, path: str) -> str:
    return path if directory == "." else f"{directory}/{path}"


def _is_safe_relative_path(value: object) -> bool:
    if not isinstance(value, str) or not value or "\\" in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and ".." not in path.parts
