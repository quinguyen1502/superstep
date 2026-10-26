from __future__ import annotations

import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from threading import Event
from typing import Callable, Dict, List, Optional, Tuple

from .adapters import AdapterError, get_adapter
from .constants import (
    ARTIFACTS_ROOT,
    DECISIONS_ROOT,
    FACTORY_CONFIG_PATH,
    FRAMEWORK_ASSETS,
    INTAKE_ROOT,
    STANDARD_AREAS,
    STANDARDS_ROOT,
    TASK_ROOT,
    TASK_STATES,
    TOOL_POLICY_PATH,
    TOOL_IDS,
)
from .discovery import render_import_assessment, scan_project
from .errors import FactoryError  # re-exported: callers import it from here
from .models import FactoryConfig, ImportAction, ImportPlan, ProjectIntake
from .renderers import (
    render_bundle,
    render_project_specs,
    render_standard,
    render_task,
    slugify,
)
from .guidance import refinement_headings


def framework_root() -> Path:
    return Path(__file__).resolve().parents[2]


def validate_project_name(project_name: str) -> None:
    if not project_name or project_name.strip() != project_name:
        raise FactoryError("Project name must not be empty or padded with whitespace.")
    if project_name in {".", ".."}:
        raise FactoryError("Project name must be a folder name, not a relative path marker.")
    if any(separator in project_name for separator in ("/", "\\")):
        raise FactoryError("Project name must not contain path separators.")


def validate_factory_source(factory_source: Path) -> None:
    missing = [asset for asset in FRAMEWORK_ASSETS if not (factory_source / asset).exists()]
    if missing:
        raise FactoryError(f"Factory source is missing required assets: {', '.join(missing)}")


def write_file(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def create_state_directories(project_dir: Path) -> None:
    directories = [STANDARDS_ROOT, DECISIONS_ROOT, ARTIFACTS_ROOT, INTAKE_ROOT]
    directories.extend(f"{TASK_ROOT}/{state}" for state in TASK_STATES)
    for directory in directories:
        (project_dir / directory).mkdir(parents=True, exist_ok=True)
    for directory in (DECISIONS_ROOT, ARTIFACTS_ROOT):
        gitkeep = project_dir / directory / ".gitkeep"
        if not gitkeep.exists():
            write_file(gitkeep, "")
    for state in TASK_STATES:
        gitkeep = project_dir / TASK_ROOT / state / ".gitkeep"
        if not gitkeep.exists():
            write_file(gitkeep, "")


def build_config(intake: ProjectIntake, link_mode: str = "copy") -> FactoryConfig:
    return FactoryConfig(
        enabled_tools=list(intake.tools),
        default_refiner=intake.refiner,
        refinement_timeout_seconds=intake.refinement_timeout_seconds,
        factory_link_mode=link_mode,
        integration_branch="develop",
    )


def create_project_structure(
    project_dir: Path,
    project_name: str,
    intake: Optional[ProjectIntake] = None,
    config: Optional[FactoryConfig] = None,
    specs_markdown: Optional[str] = None,
) -> None:
    project_dir.mkdir(parents=True, exist_ok=True)
    create_state_directories(project_dir)
    intake = intake or ProjectIntake(project_name=project_name)
    config = config or build_config(intake)
    for relative_path, content in render_project_files(
        intake, config, specs_markdown=specs_markdown
    ).items():
        write_file(project_dir / relative_path, content)


def render_project_files(
    intake: ProjectIntake,
    config: FactoryConfig,
    specs_markdown: Optional[str] = None,
) -> Dict[str, str]:
    files = render_bundle(intake, config)
    if specs_markdown is not None:
        files["project-specs.md"] = specs_markdown
    for area in STANDARD_AREAS:
        files[f"{STANDARDS_ROOT}/{area}.md"] = render_standard(area.title())
    items = [item.strip().lstrip("-* ").strip() for item in intake.mvp_scope.splitlines()]
    for index, item in enumerate((item for item in items if item), start=2):
        task_id = f"TASK-{index:04d}"
        filename = f"{task_id}-{slugify(item)}.md"
        files[f"{TASK_ROOT}/backlog/{filename}"] = render_task(
            project=intake.project_name,
            task_id=task_id,
            title=item,
            status="backlog",
            objective=f"Deliver the approved MVP outcome: {item}",
            expected_outputs=(
                "A refined task with linked requirements and validation evidence.",
            ),
            validation_plan=("Define acceptance criteria before moving this task to todo.",),
        )
    return files


def try_add_submodule(project_dir: Path, factory_source: Path) -> str:
    if not shutil.which("git"):
        return "copy"
    try:
        run(["git", "init"], cwd=project_dir)
        run(["git", "submodule", "add", str(factory_source), ".factory"], cwd=project_dir)
        return "submodule"
    except (subprocess.CalledProcessError, OSError):
        remove_path(project_dir / ".factory")
        remove_path(project_dir / ".gitmodules")
        return "copy"


def copy_factory_assets(factory_source: Path, destination: Path) -> None:
    if destination.exists():
        remove_path(destination)
    destination.mkdir(parents=True)
    for asset in FRAMEWORK_ASSETS:
        source = factory_source / asset
        target = destination / asset
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        else:
            shutil.copy2(source, target)


def initialize_project(
    project_name: str,
    target_dir: Path,
    factory_source: Path,
    intake: Optional[ProjectIntake] = None,
    force_copy: bool = False,
    specs_markdown: Optional[str] = None,
) -> Tuple[Path, str]:
    validate_project_name(project_name)
    validate_factory_source(factory_source)
    target_dir.mkdir(parents=True, exist_ok=True)
    project_dir = target_dir / project_name
    if project_dir.exists():
        raise FactoryError(f"Project path already exists: {project_dir}")
    intake = intake or ProjectIntake(project_name=project_name)
    intake.project_name = project_name
    try:
        intake.validate()
    except ValueError as exc:
        raise FactoryError(str(exc)) from exc

    with tempfile.TemporaryDirectory(prefix=f".{project_name}-factory-", dir=target_dir) as temp_dir:
        stage_project = Path(temp_dir) / project_name
        stage_project.mkdir(parents=True)
        link_result = "copy"
        if not force_copy:
            link_result = try_add_submodule(stage_project, factory_source)
        if link_result != "submodule":
            copy_factory_assets(factory_source, stage_project / ".factory")
            link_result = "copy"
        create_project_structure(
            stage_project,
            project_name,
            intake=intake,
            config=build_config(intake, link_mode=link_result),
            specs_markdown=specs_markdown,
        )
        stage_project.replace(project_dir)
    return project_dir, link_result


def refine_specs(
    intake: ProjectIntake,
    timeout: int = 300,
    progress: Optional[Callable[[str], None]] = None,
    cancel_event: Optional[Event] = None,
) -> Tuple[str, Optional[str]]:
    if progress is not None:
        progress("Preparing deterministic project specs draft…")
    deterministic = render_project_specs(intake)
    input_yaml = intake.to_yaml()
    timestamp = datetime.now(timezone.utc).isoformat()
    input_hash = sha256(input_yaml.encode("utf-8")).hexdigest()
    if not intake.use_ai or not intake.refiner:
        intake.refinement = {
            "status": "deterministic",
            "tool": intake.refiner,
            "timestamp": timestamp,
            "input_sha256": input_hash,
            "output_sha256": sha256(deterministic.encode("utf-8")).hexdigest(),
        }
        if progress is not None:
            progress("Deterministic project specs draft is ready.")
        return deterministic, None
    try:
        if progress is not None:
            progress("Preparing isolated refinement staging directory…")
        result = get_adapter(intake.refiner).refine(
            intake_yaml=input_yaml,
            template=deterministic,
            timeout=timeout,
            progress=progress,
            cancel_event=cancel_event,
            sections=list(refinement_headings(intake.refinement_sections)),
        )
    except AdapterError as exc:
        intake.refinement = {
            "status": (
                "cancelled"
                if cancel_event is not None and cancel_event.is_set()
                else "failed"
            ),
            "tool": intake.refiner,
            "timestamp": timestamp,
            "input_sha256": input_hash,
            "output_sha256": sha256(deterministic.encode("utf-8")).hexdigest(),
            "error": str(exc),
        }
        if progress is not None:
            progress(f"Refinement unavailable: {exc}")
        return deterministic, str(exc)
    intake.refinement = {
        "status": "refined",
        "tool": intake.refiner,
        "timestamp": timestamp,
        "input_sha256": input_hash,
        "output_sha256": sha256(result.markdown.encode("utf-8")).hexdigest(),
        "assumptions": result.assumptions,
        "open_questions": result.open_questions,
        "target_sections": list(intake.refinement_sections),
    }
    if progress is not None:
        progress("Refined project specs are ready for review.")
    return result.markdown, None


def load_intake(project_dir: Path) -> ProjectIntake:
    intake_path = project_dir / INTAKE_ROOT / "project-specs-input.yaml"
    if intake_path.exists():
        try:
            return ProjectIntake.from_yaml(intake_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise FactoryError(f"Invalid project intake: {exc}") from exc
    specs_path = project_dir / "project-specs.md"
    raw_draft = specs_path.read_text(encoding="utf-8") if specs_path.exists() else ""
    return ProjectIntake(project_name=project_dir.name, raw_draft=raw_draft)


def publish_specs(
    project_dir: Path,
    intake: ProjectIntake,
    markdown: str,
    config: Optional[FactoryConfig] = None,
) -> None:
    specs_path = project_dir / "project-specs.md"
    previous_path = project_dir / INTAKE_ROOT / "project-specs.previous.md"
    if specs_path.exists():
        write_file(previous_path, specs_path.read_text(encoding="utf-8"))
    write_file(project_dir / INTAKE_ROOT / "project-specs-input.yaml", intake.to_yaml())
    atomic_write(specs_path, markdown)
    if config is not None:
        config.enabled_tools = list(intake.tools)
        config.default_refiner = intake.refiner
        config.refinement_timeout_seconds = intake.refinement_timeout_seconds
        atomic_write(project_dir / FACTORY_CONFIG_PATH, config.to_yaml())


def load_config(project_dir: Path) -> FactoryConfig:
    config_path = project_dir / FACTORY_CONFIG_PATH
    if not config_path.exists():
        raise FactoryError(f"Missing factory config: {FACTORY_CONFIG_PATH}")
    try:
        return FactoryConfig.from_yaml(config_path.read_text(encoding="utf-8"))
    except ValueError as exc:
        raise FactoryError(str(exc)) from exc


def plan_import(
    project_dir: Path,
    factory_source: Path,
    intake: Optional[ProjectIntake] = None,
) -> ImportPlan:
    if not project_dir.is_dir():
        raise FactoryError(f"Project directory does not exist: {project_dir}")
    validate_factory_source(factory_source)
    intake = intake or ProjectIntake(project_name=project_dir.name)
    scan = scan_project(project_dir)
    if (project_dir / "project-specs.md").is_file() and not intake.raw_draft:
        intake.raw_draft = (project_dir / "project-specs.md").read_text(encoding="utf-8")
    for command_name, command in scan.commands.items():
        if not intake.commands.get(command_name):
            intake.commands[command_name] = command
    config = build_config(intake)
    config.integration_branch = scan.integration_branch
    proposed = render_bundle(intake, config)
    proposed[".factory-state/artifacts/DISC-0001-project-context.md"] = render_import_assessment(
        project_dir.name, scan
    )
    for area in STANDARD_AREAS:
        proposed[f"{STANDARDS_ROOT}/{area}.md"] = render_standard(area.title())

    actions: List[ImportAction] = []
    for relative_path, content in proposed.items():
        path = project_dir / relative_path
        if not path.exists():
            actions.append(ImportAction(relative_path, "create", "path is missing", content))
        elif not path.is_file():
            actions.append(ImportAction(relative_path, "invalid", "expected a file"))
        elif path.read_text(encoding="utf-8") == content:
            actions.append(ImportAction(relative_path, "keep", "content already matches"))
        else:
            actions.append(ImportAction(relative_path, "conflict", "existing content is preserved", content))

    factory_dir = project_dir / ".factory"
    configured_submodule = has_factory_submodule(project_dir)
    if not factory_dir.exists() and configured_submodule:
        actions.append(
            ImportAction(
                ".factory",
                "create",
                "configured factory submodule is uninitialized; apply initializes it",
            )
        )
    elif not factory_dir.exists():
        actions.append(ImportAction(".factory", "create", "factory framework is missing"))
    elif not factory_dir.is_dir():
        actions.append(ImportAction(".factory", "invalid", "expected a directory"))
    elif (factory_dir / "AGENTS.md").exists():
        actions.append(ImportAction(".factory", "keep", "factory framework is available"))
    elif configured_submodule:
        actions.append(
            ImportAction(
                ".factory",
                "create",
                "configured factory submodule is uninitialized; apply initializes it",
            )
        )
    else:
        actions.append(ImportAction(".factory", "invalid", "factory AGENTS.md is unavailable"))
    return ImportPlan(str(project_dir), actions)


def apply_import(
    plan: ImportPlan,
    factory_source: Path,
    force_copy: bool = False,
    conflict_resolutions: Optional[Dict[str, str]] = None,
) -> str:
    project_dir = Path(plan.project_dir)
    if plan.invalid:
        raise FactoryError("Import plan contains invalid paths; resolve them before apply.")
    resolutions = conflict_resolutions or {}
    conflict_paths = {action.path for action in plan.conflicts}
    unknown_resolutions = sorted(set(resolutions) - conflict_paths)
    if unknown_resolutions:
        raise FactoryError(
            f"Import resolutions reference unknown conflicts: {', '.join(unknown_resolutions)}"
        )
    create_state_directories(project_dir)
    proposal_root = project_dir / ".factory-state" / "import" / "proposals"
    instruction_conflict = False
    for action in plan.actions:
        if action.status == "create" and action.path != ".factory" and action.proposed_content is not None:
            path = project_dir / action.path
            if not path.exists():
                write_file(path, action.proposed_content)
        elif action.status == "conflict" and action.proposed_content is not None:
            write_file(proposal_root / action.path, action.proposed_content)
            if action.path in resolutions:
                atomic_write(project_dir / action.path, resolutions[action.path])
            elif action.path in {
                "AGENTS.md",
                ".claude/CLAUDE.md",
                TOOL_POLICY_PATH,
            }:
                instruction_conflict = True

    link_result = "existing"
    factory_action = next(
        (
            action
            for action in plan.actions
            if action.path == ".factory" and action.status == "create"
        ),
        None,
    )
    if factory_action:
        if "configured factory submodule" in factory_action.reason:
            try:
                run(["git", "submodule", "update", "--init", ".factory"], cwd=project_dir)
            except (subprocess.CalledProcessError, OSError) as exc:
                raise FactoryError(
                    "Unable to initialize the configured .factory submodule; "
                    "check credentials and network access."
                ) from exc
            if not (project_dir / ".factory" / "AGENTS.md").exists():
                raise FactoryError("Initialized .factory submodule does not contain AGENTS.md.")
            link_result = "submodule"
        else:
            if not force_copy:
                link_result = try_add_submodule(project_dir, factory_source)
            if force_copy or link_result != "submodule":
                copy_factory_assets(factory_source, project_dir / ".factory")
                link_result = "copy"

    config_was_created = any(
        action.path == FACTORY_CONFIG_PATH and action.status == "create"
        for action in plan.actions
    )
    if config_was_created:
        config_path = project_dir / FACTORY_CONFIG_PATH
        config = FactoryConfig.from_yaml(config_path.read_text(encoding="utf-8"))
        if link_result == "existing":
            gitmodules = project_dir / ".gitmodules"
            is_submodule = gitmodules.exists() and "path = .factory" in gitmodules.read_text(
                encoding="utf-8"
            )
            config.factory_link_mode = "submodule" if is_submodule else "copy"
        else:
            config.factory_link_mode = link_result
        atomic_write(config_path, config.to_yaml())

    import_root = project_dir / ".factory-state" / "import"
    write_file(import_root / "import-plan.txt", plan.render() + "\n")
    incomplete = import_root / "INCOMPLETE"
    if instruction_conflict:
        write_file(
            incomplete,
            "Instruction conflicts must be reviewed and merged before factory workflows run.\n",
        )
    elif incomplete.exists():
        incomplete.unlink()
    return link_result


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False, prefix=f".{path.name}."
    ) as handle:
        handle.write(content)
        temp_path = Path(handle.name)
    temp_path.replace(path)


def run(command: List[str], cwd: Path) -> None:
    subprocess.run(
        command,
        cwd=cwd,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def has_factory_submodule(project_dir: Path) -> bool:
    gitmodules = project_dir / ".gitmodules"
    if not gitmodules.is_file():
        return False
    content = gitmodules.read_text(encoding="utf-8")
    return "path = .factory" in content or "path=.factory" in content


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()
