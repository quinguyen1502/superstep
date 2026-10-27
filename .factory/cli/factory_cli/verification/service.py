from __future__ import annotations

import hashlib
import itertools
import json
import os
import shlex
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, Iterator, List, Optional, Sequence, Tuple

import yaml

from ..constants import (
    TOOL_POLICY_PATH,
    VERIFICATION_KINDS,
    VERIFICATION_METADATA_PATH,
    VERIFICATION_QUICK_KINDS,
    VERIFICATION_ROOT,
)
from ..project import atomic_write
from ..tooling import CommandPolicy, load_tool_policy
from .models import VerificationCheck, VerificationPlan, VerificationResult


VERIFICATION_SCHEMA_VERSION = 1
VERIFICATION_TIMEOUT_SECONDS = 300
PROFILES = {"quick", "full"}
CHECK_KINDS = set(VERIFICATION_KINDS)
QUICK_KINDS = set(VERIFICATION_QUICK_KINDS)
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
LEGACY_EVIDENCE_WARNING = (
    "verification evidence still records input hashes or absolute executable "
    "paths; re-run factory verify to replace it"
)


class VerificationError(Exception):
    """Blocking verification planning, execution, or validation problem."""


def create_verification_plan(
    project_dir: Path,
    *,
    profile: str = "quick",
    selected_kinds: Sequence[str] = (),
) -> VerificationPlan:
    project_dir = project_dir.resolve()
    if not project_dir.is_dir():
        raise VerificationError(f"Project directory does not exist: {project_dir}")
    if profile not in PROFILES:
        raise VerificationError(f"Unsupported verification profile: {profile}")
    invalid = sorted(set(selected_kinds) - CHECK_KINDS)
    if invalid:
        raise VerificationError(f"Unsupported verification checks: {', '.join(invalid)}")
    plan = VerificationPlan(
        project_dir=str(project_dir),
        source_sha256="",
        profile=profile,
        selected_kinds=tuple(selected_kinds),
    )
    requested = set(selected_kinds) if selected_kinds else None
    if not _checks_from_policy(project_dir, plan):
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
        if plan.origin == "policy":
            plan.errors.append(
                "no verification commands in tool-policy.yaml match this profile"
            )
        else:
            plan.errors.append("no supported verification checks were discovered")
    if plan.origin == "discovery" and plan.checks and not plan.errors:
        if (project_dir / TOOL_POLICY_PATH).is_file():
            plan.warnings.append(
                "tool-policy.yaml has no verification commands; verify run will "
                "record the discovered commands there"
            )
        else:
            plan.warnings.append(
                "no tool-policy.yaml; discovered commands are used for this run only"
            )
    plan.fingerprint = _fingerprint(plan.checks)
    return plan


def _checks_from_policy(project_dir: Path, plan: VerificationPlan) -> bool:
    """Use tool-policy commands when the file declares any verification command.

    An empty command map returns False so discovery can fill it. A broken
    policy is an error and does not fall through to discovery.
    """
    path = project_dir / TOOL_POLICY_PATH
    if not path.is_file():
        return False
    try:
        policy = load_tool_policy(project_dir)
    except ValueError as exc:
        plan.origin = "policy"
        plan.errors.append(f"invalid tool policy: {exc}")
        return True
    found = False
    for name, spec in policy.commands.items():
        kind = spec.kind.strip() or (name if name in CHECK_KINDS else "")
        if kind not in CHECK_KINDS or not spec.command.strip():
            continue
        found = True
        working_dir = spec.cwd.strip() or "."
        cwd = project_dir / working_dir
        try:
            argv = shlex.split(spec.command)
        except ValueError as exc:
            plan.errors.append(f"invalid verification command {name}: {exc}")
            continue
        if not argv:
            plan.errors.append(f"invalid verification command {name}: command is empty")
            continue
        if not cwd.is_dir():
            plan.errors.append(
                f"{name}: working directory does not exist: {working_dir}"
            )
            continue
        problem = _portable_command_problem(cwd, argv)
        if problem:
            plan.errors.append(f"{name}: {problem}")
            continue
        plan.checks.append(
            VerificationCheck(
                check_id=f"policy:{name}",
                kind=kind,
                working_dir=working_dir,
                argv=argv,
                source=TOOL_POLICY_PATH,
                timeout_seconds=spec.timeout or None,
            )
        )
    if not found and not plan.errors:
        return False
    plan.origin = "policy"
    return True


def _portable_command_problem(cwd: Path, argv: Sequence[str]) -> Optional[str]:
    token = argv[0]
    if Path(token).is_absolute():
        return f"verification command must not use an absolute path: {token}"
    if "/" in token or token.startswith("."):
        if not (cwd / token).is_file():
            return f"{token} was not found in {cwd}"
        return None
    if shutil.which(token) is None:
        return f"{token} was not found on PATH"
    return None


def _fingerprint(checks: Sequence[VerificationCheck]) -> str:
    payload = [
        {
            "command": check.command_display,
            "kind": check.kind,
            "working_dir": check.working_dir,
        }
        for check in checks
    ]
    rendered = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(rendered.encode("utf-8")).hexdigest()


def _rebase(plan: VerificationPlan) -> VerificationPlan:
    fresh = create_verification_plan(
        Path(plan.project_dir),
        profile=plan.profile,
        selected_kinds=plan.selected_kinds,
    )
    if fresh.fingerprint != plan.fingerprint:
        raise VerificationError(
            "Verification commands changed after planning; create a new plan."
        )
    return fresh


def _command_name(check: VerificationCheck, taken: Iterable[str]) -> str:
    """A policy name for a discovered check that no other command uses.

    ``<dir>-<kind>`` (``<kind>`` at the root) first. Two checks of one kind in
    one directory, such as npm and pytest tests at the root, or a name the
    policy already uses for another command, get the tool from the check ID
    (``test-python``) and then a number.
    """
    taken = set(taken)
    directory = PurePosixPath(check.working_dir.replace("\\", "/")).as_posix()
    base = (
        check.kind
        if directory in {"", "."}
        else f"{directory.replace('/', '-')}-{check.kind}"
    )
    tool = check.check_id.split(":", 1)[0]
    candidates = itertools.chain(
        (base, f"{base}-{tool}"),
        (f"{base}-{tool}-{number}" for number in itertools.count(2)),
    )
    return next(name for name in candidates if name not in taken)


def _record_discovered_commands(project_dir: Path, plan: VerificationPlan) -> None:
    policy = load_tool_policy(project_dir)
    for check in plan.checks:
        taken = [name for name, spec in policy.commands.items() if spec.command.strip()]
        name = _command_name(check, taken)
        policy.commands[name] = CommandPolicy(
            command=check.command_display,
            evidence="Expected",
            cwd="" if check.working_dir in {"", "."} else check.working_dir,
            kind="" if name == check.kind else check.kind,
        )
    policy.validate()
    atomic_write(project_dir / TOOL_POLICY_PATH, policy.to_yaml())


def _resolved_argv(argv: Sequence[str]) -> List[str]:
    token = argv[0]
    if "/" in token or token.startswith("."):
        return list(argv)
    resolved = shutil.which(token)
    if not resolved:
        raise VerificationError(f"{token} was not found on PATH")
    return [resolved, *list(argv[1:])]


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
        if shutil.which(manager) is None:
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
                [manager, script]
                if manager == "yarn"
                else [manager, "run", script]
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
        if shutil.which("flutter") is None:
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
                    argv=["flutter", *arguments],
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
    if shutil.which("dotnet") is None:
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
                    ["dotnet", "test", manifest.name, "--no-restore"],
                    relative,
                ),
                VerificationCheck(
                    f"dotnet:{working_dir}:build",
                    "build",
                    working_dir,
                    ["dotnet", "build", manifest.name, "--no-restore"],
                    relative,
                ),
            )
        )


def _discover_go_checks(project_dir: Path, plan: VerificationPlan) -> None:
    for manifest in _find_name(project_dir, "go.mod"):
        relative = manifest.relative_to(project_dir).as_posix()
        working_dir = manifest.parent.relative_to(project_dir).as_posix() or "."
        if shutil.which("go") is None:
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
                    ["go", *arguments],
                    relative,
                )
            )


def run_verification_plan(
    plan: VerificationPlan,
    *,
    timeout_seconds: Optional[int] = None,
) -> List[VerificationResult]:
    """Run the plan's checks. A check's own ``timeout`` from the tool policy
    wins over ``timeout_seconds``, which defaults to 300 seconds."""
    if not plan.ready:
        raise VerificationError("Verification plan is not ready; resolve its errors first.")
    plan = _rebase(plan)
    project_dir = Path(plan.project_dir)
    if plan.origin == "discovery" and (project_dir / TOOL_POLICY_PATH).is_file():
        full = create_verification_plan(project_dir, profile="full")
        if full.origin == "discovery" and full.ready:
            _record_discovered_commands(project_dir, full)
            plan = _rebase(plan)
    results: List[VerificationResult] = []
    for check in plan.checks:
        started = datetime.now(timezone.utc).isoformat()
        before = time.monotonic()
        try:
            argv = _resolved_argv(check.argv)
        except VerificationError as exc:
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
            continue
        try:
            completed = subprocess.run(
                argv,
                cwd=project_dir / check.working_dir,
                env=_verification_environment(),
                text=True,
                capture_output=True,
                timeout=check.timeout_seconds
                or timeout_seconds
                or VERIFICATION_TIMEOUT_SECONDS,
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
            error = str(exc)
            if isinstance(exc, subprocess.TimeoutExpired):
                error += (
                    f". Raise it with `timeout` on this command in {TOOL_POLICY_PATH},"
                    " or with `factory verify run --timeout`."
                )
            results.append(
                VerificationResult(
                    check=check,
                    status="failed",
                    returncode=None,
                    started_at=started,
                    duration_seconds=time.monotonic() - before,
                    error=error,
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
        results = data.get("results")
        if not isinstance(results, list):
            raise ValueError("results must be a list")
    except (OSError, ValueError, yaml.YAMLError) as exc:
        errors.append(f"invalid verification metadata: {exc}")
        return errors, warnings
    if data.get("status") == "failed":
        errors.append("latest project verification failed")
    legacy = isinstance(data.get("inputs"), dict) and bool(data.get("inputs"))
    for result in results:
        if not isinstance(result, dict) or result.get("status") not in {"passed", "failed"}:
            errors.append("invalid verification result metadata")
            continue
        argv = result.get("argv")
        if isinstance(argv, list) and any(
            isinstance(item, str) and Path(item).is_absolute() for item in argv
        ):
            legacy = True
    if legacy:
        warnings.append(LEGACY_EVIDENCE_WARNING)
    return errors, warnings


def render_verification_review(plan: VerificationPlan) -> str:
    if plan.origin == "policy":
        intro = "Factory will run the verification commands declared in tool-policy.yaml."
    else:
        intro = (
            "Factory will run deterministic validation checks discovered from "
            "project manifests. verify run records them into tool-policy.yaml when "
            "that file exists and does not yet declare verification commands."
        )
    return "\n".join(
        (
            "# Project verification review",
            "",
            intro,
            (
                "Commands are argument lists, not shell scripts. Install, run, "
                "migration, server, and deployment commands are not included."
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
    # The committed record is the command and its outcome. Absolute paths,
    # per-file hashes, output hashes, and timestamped run copies change on
    # every machine and every edit, so they are not written.
    status = "passed" if all(result.status == "passed" for result in results) else "failed"
    data = {
        "schema_version": VERIFICATION_SCHEMA_VERSION,
        "status": status,
        "profile": plan.profile,
        "results": [result.to_dict() for result in results],
    }
    atomic_write(
        project_dir / VERIFICATION_METADATA_PATH,
        yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
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
    if shutil.which("mvn") is None:
        return None
    return "mvn"
