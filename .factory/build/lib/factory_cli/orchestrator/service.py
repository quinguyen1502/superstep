from __future__ import annotations

import re
import shlex
import subprocess
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml

from ..adapters import detect_tools, get_adapter
from ..constants import (
    ORCHESTRATION_BRIEF_NAME,
    ORCHESTRATION_INCOMPLETE_PATH,
    ORCHESTRATION_METADATA_PATH,
    ORCHESTRATION_WORKTREE_DIR,
    TASK_ROOT,
)
from ..project import atomic_write, load_config
from ..storage import open_store
from ..tasks import move_task, validate_project_task_root
from .models import OrchestratorAssignment, OrchestratorPlan, OrchestratorRecord


ORCHESTRATION_SCHEMA_VERSION = 1
DEFAULT_MAX_PARALLEL = 2
_GIT_LOCK = threading.Lock()


class OrchestratorError(Exception):
    """Raised when the multi-tool orchestrator cannot prepare or run work."""


def _git(args: List[str], cwd: Path) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:  # pragma: no cover - git missing is environmental
        raise OrchestratorError(f"Unable to run git: {exc}") from exc


def _git_ok(args: List[str], cwd: Path) -> bool:
    return _git(args, cwd).returncode == 0


def _require_git_repo(project_dir: Path) -> None:
    if not _git_ok(["rev-parse", "--is-inside-work-tree"], project_dir):
        raise OrchestratorError(
            f"Not a git repository: {project_dir}. Orchestration needs git worktrees."
        )


def _branch_for(task_id: str, slug: str) -> str:
    branch_id = task_id.lower()
    if branch_id.startswith("task-"):
        branch_id = branch_id[5:]
    return f"factory/task-{branch_id}-{slug}"


def _worktree_dir(project_dir: Path) -> Path:
    return (project_dir / ORCHESTRATION_WORKTREE_DIR).resolve()


def _ensure_worktree_root(project_dir: Path) -> None:
    root = _worktree_dir(project_dir)
    root.mkdir(parents=True, exist_ok=True)
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "# Factory orchestration worktrees are local-only checkouts.\n"
            "*\n"
            "!.gitignore\n",
            encoding="utf-8",
        )


def _worktree_leaf(branch: str) -> str:
    return branch.replace("/", "-")


def _parse_task(path: Path) -> Tuple[str, str, List[str]]:
    """Return (task_id, objective/title, related artifact paths) from a task file."""
    text = path.read_text(encoding="utf-8")
    task_id = ""
    match = re.search(r"^- Task ID:\s*(.+)$", text, flags=re.MULTILINE)
    if match:
        task_id = match.group(1).strip()
    objective = ""
    objective_match = re.search(
        r"^## Objective\s*\n+(.+?)\s*$", text, flags=re.MULTILINE
    )
    if objective_match:
        objective = objective_match.group(1).strip()
    related = re.findall(r"`([^`]+)`", _section(text, "Related Artifacts"))
    return task_id, objective, related


def _section(text: str, heading: str) -> str:
    pattern = re.compile(
        rf"^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    return match.group(1) if match else ""


def _todo_task_files(project_dir: Path) -> List[Path]:
    todo_dir = project_dir / TASK_ROOT / "todo"
    if not todo_dir.is_dir():
        return []
    return sorted(todo_dir.glob("*.md"))


def create_orchestrator_plan(
    project_dir: Path,
    tools: Optional[List[str]] = None,
    max_parallel: Optional[int] = None,
) -> OrchestratorPlan:
    validate_project_task_root(project_dir)
    config = load_config(project_dir)
    integration_branch = config.integration_branch
    plan = OrchestratorPlan(
        project_dir=str(project_dir),
        integration_branch=integration_branch,
    )

    installed = {tool for tool, ok in detect_tools().items() if ok}
    requested = list(dict.fromkeys(tools)) if tools else list(config.enabled_tools)
    unknown = [tool for tool in requested if tool not in detect_tools()]
    for tool in unknown:
        plan.errors.append(f"Unknown AI tool: {tool}")
    available = [tool for tool in requested if tool in installed]
    for tool in requested:
        if tool in installed:
            continue
        if tool in unknown:
            continue
        plan.warnings.append(f"Tool not installed, skipping: {tool}")
    plan.available_tools = available

    if not _git_ok(["rev-parse", "--is-inside-work-tree"], project_dir):
        plan.errors.append(
            "Not a git repository; orchestration needs git worktrees."
        )
    elif not _git_ok(["rev-parse", "--verify", integration_branch], project_dir):
        plan.errors.append(
            f"Integration branch not found: {integration_branch}. "
            "Create it or set integration_branch in factory.yaml."
        )

    task_files = _todo_task_files(project_dir)
    if not task_files:
        plan.warnings.append("No tasks in todo; nothing to orchestrate.")
    if not available and task_files:
        plan.errors.append(
            "No enabled AI tool is installed; cannot assign tasks."
        )

    store = open_store(project_dir, config)
    worktree_root = _worktree_dir(project_dir)
    for index, task_path in enumerate(task_files):
        task_id, objective, _ = _parse_task(task_path)
        if not task_id:
            plan.warnings.append(f"Skipping unparseable task: {task_path.name}")
            continue
        budget_key = f"task:{task_id}"
        limit = config.budgets.get(budget_key)
        if limit:
            used = store.usage_for_key(budget_key)
            if used >= limit:
                detail = f"{task_id} is over its token budget ({used}/{limit})"
                if config.budget_enforcement == "block":
                    plan.warnings.append(f"Blocked: {detail}.")
                    continue
                plan.warnings.append(f"Over budget: {detail}.")
        stem = task_path.stem
        prefix = f"{task_id}-"
        slug = stem[len(prefix):] if stem.startswith(prefix) else stem
        branch = _branch_for(task_id, slug)
        worktree_path = worktree_root / _worktree_leaf(branch)
        if available:
            tool_id = available[index % len(available)]
        else:
            tool_id = ""
        if _git_ok(["rev-parse", "--verify", branch], project_dir):
            plan.errors.append(f"Branch already exists: {branch}")
        if worktree_path.exists():
            plan.errors.append(f"Worktree path already exists: {worktree_path}")
        if tool_id:
            plan.assignments.append(
                OrchestratorAssignment(
                    task_id=task_id,
                    task_title=objective or slug,
                    task_path=str(task_path.relative_to(project_dir)),
                    tool_id=tool_id,
                    branch=branch,
                    worktree_path=str(worktree_path),
                )
            )
    return plan


def _render_brief(
    assignment: OrchestratorAssignment,
    integration_branch: str,
    related: List[str],
) -> str:
    related_lines = "\n".join(f"- `{path}`" for path in related) or "- (none recorded)"
    return f"""# Orchestration Brief

This worktree was prepared by `factory orchestrate` for one task. It is isolated
from other tasks. Drive the work here with the assigned tool, then follow the
normal Factory delivery flow.

## Assignment

- Task ID: {assignment.task_id}
- Title: {assignment.task_title}
- Assigned tool: {assignment.tool_id}
- Task branch: {assignment.branch}
- Integration branch: {integration_branch}
- Task artifact: `{assignment.task_path}`

## Related Artifacts

{related_lines}

## Rules

- This task uses exactly one branch and one pull request.
- Do not merge into `{integration_branch}` without explicit owner approval.
- Update the task artifact with implementation notes and validation performed.
- This brief file is local only; do not commit it.
"""


def _exclude_brief(worktree_path: Path) -> None:
    result = _git(["rev-parse", "--git-path", "info/exclude"], worktree_path)
    if result.returncode != 0:
        return
    exclude_path = Path(result.stdout.strip())
    if not exclude_path.is_absolute():
        exclude_path = (worktree_path / exclude_path).resolve()
    try:
        existing = (
            exclude_path.read_text(encoding="utf-8")
            if exclude_path.exists()
            else ""
        )
        if ORCHESTRATION_BRIEF_NAME not in existing.splitlines():
            exclude_path.parent.mkdir(parents=True, exist_ok=True)
            with exclude_path.open("a", encoding="utf-8") as handle:
                if existing and not existing.endswith("\n"):
                    handle.write("\n")
                handle.write(f"{ORCHESTRATION_BRIEF_NAME}\n")
    except OSError:
        return


def _setup_assignment(
    project_dir: Path,
    assignment: OrchestratorAssignment,
    integration_branch: str,
    launch: bool,
) -> OrchestratorRecord:
    worktree_path = Path(assignment.worktree_path)
    with _GIT_LOCK:
        add = _git(
            [
                "worktree",
                "add",
                str(worktree_path),
                "-b",
                assignment.branch,
                integration_branch,
            ],
            project_dir,
        )
    if add.returncode != 0:
        detail = add.stderr.strip() or add.stdout.strip() or "unknown error"
        raise OrchestratorError(
            f"git worktree add failed for {assignment.task_id}: {detail}"
        )

    _, _, related = _parse_task(project_dir / assignment.task_path)
    brief_path = worktree_path / ORCHESTRATION_BRIEF_NAME
    brief_path.write_text(
        _render_brief(assignment, integration_branch, related), encoding="utf-8"
    )
    _exclude_brief(worktree_path)

    launch_command: Optional[str] = None
    adapter = get_adapter(assignment.tool_id)
    executable = adapter.detect()
    if executable:
        argv = adapter.launch_command(executable, brief_path)
        launch_command = shlex.join(argv)
        if launch:
            try:
                subprocess.Popen(argv, cwd=worktree_path)
            except OSError as exc:
                raise OrchestratorError(
                    f"Failed to launch {assignment.tool_id} for "
                    f"{assignment.task_id}: {exc}"
                ) from exc

    return OrchestratorRecord(
        task_id=assignment.task_id,
        tool_id=assignment.tool_id,
        branch=assignment.branch,
        worktree_path=str(worktree_path),
        status="launched" if launch else "prepared",
        created_at=datetime.now(timezone.utc).isoformat(),
        launch_command=launch_command,
    )


def apply_orchestrator_plan(
    plan: OrchestratorPlan,
    launch: bool = False,
    max_parallel: Optional[int] = None,
) -> List[OrchestratorRecord]:
    if not plan.ready:
        raise OrchestratorError("Orchestration plan is not ready to apply.")
    project_dir = Path(plan.project_dir)
    _require_git_repo(project_dir)
    _ensure_worktree_root(project_dir)
    workers = max(1, max_parallel or DEFAULT_MAX_PARALLEL)

    records: List[OrchestratorRecord] = []
    failures: List[str] = []

    def worker(assignment: OrchestratorAssignment) -> Optional[OrchestratorRecord]:
        try:
            record = _setup_assignment(
                project_dir, assignment, plan.integration_branch, launch
            )
        except Exception as exc:  # noqa: BLE001 - any failure must roll back cleanly
            _rollback_worktree(project_dir, Path(assignment.worktree_path), assignment.branch)
            failures.append(f"{assignment.task_id}: {exc}")
            return None
        return record

    with ThreadPoolExecutor(max_workers=workers) as executor:
        for record in executor.map(worker, plan.assignments):
            if record is not None:
                records.append(record)

    # Move successfully prepared tasks todo -> doing.
    for record in records:
        move_task(project_dir, record.task_id, "doing")

    _write_state(project_dir, records)
    incomplete = project_dir / ORCHESTRATION_INCOMPLETE_PATH
    if failures:
        atomic_write(incomplete, "\n".join(failures) + "\n")
    elif incomplete.exists():
        incomplete.unlink()
    return records


def _rollback_worktree(project_dir: Path, worktree_path: Path, branch: str) -> None:
    with _GIT_LOCK:
        if worktree_path.exists():
            _git(["worktree", "remove", "--force", str(worktree_path)], project_dir)
        _git(["worktree", "prune"], project_dir)
        if _git_ok(["rev-parse", "--verify", branch], project_dir):
            _git(["branch", "-D", branch], project_dir)


def _write_state(project_dir: Path, records: List[OrchestratorRecord]) -> None:
    payload = {
        "schema_version": ORCHESTRATION_SCHEMA_VERSION,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "records": [record.to_dict() for record in records],
    }
    atomic_write(
        project_dir / ORCHESTRATION_METADATA_PATH,
        yaml.safe_dump(payload, sort_keys=False),
    )


def load_state(project_dir: Path) -> List[OrchestratorRecord]:
    path = project_dir / ORCHESTRATION_METADATA_PATH
    if not path.is_file():
        return []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise OrchestratorError(f"Invalid orchestration state: {exc}") from exc
    records = data.get("records", [])
    if not isinstance(records, list):
        raise OrchestratorError("Orchestration state records must be a list.")
    return [OrchestratorRecord.from_dict(item) for item in records]


def list_worktrees(project_dir: Path) -> Dict[str, str]:
    result = _git(["worktree", "list", "--porcelain"], project_dir)
    worktrees: Dict[str, str] = {}
    current = ""
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            current = line[len("worktree "):].strip()
        elif line.startswith("branch "):
            worktrees[current] = line[len("branch "):].strip()
    return worktrees


def orchestrator_problems(
    project_dir: Path, require_state: bool = False
) -> Tuple[List[str], List[str]]:
    errors: List[str] = []
    warnings: List[str] = []
    path = project_dir / ORCHESTRATION_METADATA_PATH
    if not path.is_file():
        if require_state:
            errors.append("No orchestration state recorded.")
        return errors, warnings
    try:
        records = load_state(project_dir)
    except OrchestratorError as exc:
        errors.append(str(exc))
        return errors, warnings
    if (project_dir / ORCHESTRATION_INCOMPLETE_PATH).exists():
        warnings.append(
            "Previous orchestration was incomplete; resolve and rerun run."
        )
    live = list_worktrees(project_dir)
    live_paths = {str(Path(p).resolve()) for p in live}
    for record in records:
        if record.status not in {"prepared", "launched"}:
            continue
        resolved = str(Path(record.worktree_path).resolve())
        if resolved not in live_paths:
            warnings.append(
                f"Recorded worktree missing for {record.task_id}: "
                f"{record.worktree_path}"
            )
    return errors, warnings


def cleanup_worktrees(
    project_dir: Path, force: bool = False
) -> Tuple[List[str], List[str]]:
    """Remove factory-created worktrees that are clean. Returns (removed, skipped)."""
    _require_git_repo(project_dir)
    records = load_state(project_dir)
    removed: List[str] = []
    skipped: List[str] = []
    remaining: List[OrchestratorRecord] = []
    for record in records:
        worktree_path = Path(record.worktree_path)
        if not worktree_path.exists():
            removed.append(record.task_id)
            continue
        dirty = _git(["status", "--porcelain"], worktree_path).stdout.strip()
        if dirty and not force:
            skipped.append(
                f"{record.task_id}: worktree has uncommitted changes"
            )
            remaining.append(record)
            continue
        with _GIT_LOCK:
            result = _git(
                ["worktree", "remove", *(["--force"] if force else []), str(worktree_path)],
                project_dir,
            )
        if result.returncode != 0:
            skipped.append(f"{record.task_id}: {result.stderr.strip()}")
            remaining.append(record)
            continue
        removed.append(record.task_id)
    _git(["worktree", "prune"], project_dir)
    _write_state(project_dir, remaining)
    return removed, skipped


def render_orchestrator_review(plan: OrchestratorPlan) -> str:
    lines = [
        "# Orchestration Review",
        "",
        f"Project: `{plan.project_dir}`",
        f"Integration branch: `{plan.integration_branch}`",
        f"Available tools: {', '.join(plan.available_tools) or '(none)'}",
        "",
        "## Assignments",
        "",
        "| Task | Tool | Branch | Worktree |",
        "| --- | --- | --- | --- |",
    ]
    for assignment in plan.assignments:
        lines.append(
            f"| {assignment.task_id} | {assignment.tool_id} | "
            f"`{assignment.branch}` | `{assignment.worktree_path}` |"
        )
    if plan.warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {message}" for message in plan.warnings)
    if plan.errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- {message}" for message in plan.errors)
    return "\n".join(lines) + "\n"
