from __future__ import annotations

import argparse
import sys
from hashlib import sha256
from pathlib import Path
from typing import List, Optional, Tuple

from .constants import (
    GC_DEFAULT_KEEP,
    PROJECT_PRESET_IDS,
    TASK_STATES,
    TOOL_IDS,
    TOOL_KIT_LEVELS,
    VERIFICATION_KINDS,
)
from .storage import StoreError
from .dependencies import (
    DependencyError,
    DependencyPlan,
    apply_dependency_plan,
    create_dependency_plan,
    dependency_problems,
)
from .guidance import apply_project_preset, refinement_headings
from .intake import (
    load_intake_yaml,
    merge_specs_into_intake,
    overlay_cli_intake,
    read_text_file,
)
from .models import ProjectIntake
from .readiness import inspect_readiness, render_readiness
from .project import (
    FactoryError,
    apply_import,
    framework_root,
    initialize_project,
    load_config,
    load_intake,
    plan_import,
    publish_specs,
    refine_specs,
    validate_factory_source,
    validate_project_name,
)
from .renderers import render_project_specs
from .skills import (
    SkillError,
    apply_plan as apply_skills_plan,
    plan_skills,
    render_apply_summary,
)
from .spec_sections import changed_sections, merge_sections
from .ids import configure_ids_parser, run_ids
from .gc import run_gc
from .tasks import archive_tasks, create_task, move_task
from .tooling import (
    apply_tooling_plan,
    default_tool_policy,
    load_tool_policy,
    overlay_tool_policy,
    parse_command_spec,
    plan_tooling,
    render_tooling_status,
    tooling_problems,
)
from .verification import (
    VerificationError,
    create_verification_plan,
    run_verification_plan,
    verification_problems,
)
from .validation import validate_project


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    args = parser.parse_args(raw_argv)
    try:
        if args.command == "init":
            return handle_init(args)
        if args.command == "import":
            return handle_import(args)
        if args.command == "specs":
            return handle_specs(args)
        if args.command == "validate":
            return validate_project(Path(args.project_dir).resolve())
        if args.command == "ready":
            return handle_ready(args)
        if args.command == "tools":
            return handle_tools(args)
        if args.command == "deps":
            return handle_dependencies(args)
        if args.command == "verify":
            return handle_verification(args)
        if args.command == "skills":
            return handle_skills(args)
        if args.command == "ids":
            return run_ids(args)
        if args.command == "gc":
            return run_gc(
                project_dir=Path(args.project_dir).resolve(),
                keep=args.keep,
                with_artifacts=args.with_artifacts,
                apply=args.apply,
                with_tasks=args.with_tasks,
                with_runs=args.with_runs,
            )
        if args.command == "task":
            if args.task_command == "create":
                return create_task(
                    project_dir=Path(args.project_dir).resolve(),
                    task_id=args.task_id,
                    title=args.title,
                    state=args.state,
                )
            if args.task_command == "move":
                return move_task(
                    project_dir=Path(args.project_dir).resolve(),
                    task_id=args.task_id,
                    target_state=args.state,
                )
            if args.task_command == "archive":
                return archive_tasks(
                    project_dir=Path(args.project_dir).resolve(),
                    state=args.state,
                    task_id=args.task_id,
                )
    except (
        FactoryError,
        DependencyError,
        VerificationError,
        SkillError,
        StoreError,
    ) as exc:
        print(f"factory: {exc}", file=sys.stderr)
        return 2
    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="factory",
        description="Bootstrap and operate AI Software Factory project repositories.",
    )
    subcommands = parser.add_subparsers(dest="command")

    init = subcommands.add_parser("init", help="Create a new factory project.")
    init.add_argument("project_name", help="Name of the project folder to create.")
    init.add_argument("-C", "--directory", default=".")
    init.add_argument("--factory-source")
    init.add_argument("--copy", action="store_true")
    init.add_argument("--tool", action="append", choices=TOOL_IDS, dest="tools")
    init.add_argument("--refiner", choices=TOOL_IDS)
    init.add_argument("--no-interactive", action="store_true")
    init.add_argument("--tool-kit", choices=TOOL_KIT_LEVELS)
    init.add_argument(
        "--preset",
        choices=PROJECT_PRESET_IDS,
        help="Fill blank stack and command fields from a starter preset (Proposed only).",
    )
    init.add_argument(
        "--intake",
        dest="intake_path",
        help="Load ProjectIntake YAML so init can run without the wizard.",
    )
    init.add_argument(
        "--from-specs",
        dest="specs_path",
        help="Publish this project-specs markdown and fill blank intake fields from it.",
    )
    skills_group = init.add_mutually_exclusive_group()
    skills_group.add_argument(
        "--with-skills",
        dest="with_skills",
        action="store_true",
        help="Emit framework skill files for enabled tools after init (default).",
    )
    skills_group.add_argument(
        "--no-skills",
        dest="with_skills",
        action="store_false",
        help="Skip emitting skill files after init.",
    )
    init.set_defaults(with_skills=True)

    import_parser = subcommands.add_parser("import", help="Import factory into an existing project.")
    import_parser.add_argument("project_dir", nargs="?", default=".")
    import_parser.add_argument("--factory-source")
    import_parser.add_argument("--copy", action="store_true")
    import_parser.add_argument("--apply", action="store_true")
    import_parser.add_argument("--tool", action="append", choices=TOOL_IDS, dest="tools")
    import_parser.add_argument("--refiner", choices=TOOL_IDS)
    import_parser.add_argument("--no-interactive", action="store_true")
    import_parser.add_argument("--tool-kit", choices=TOOL_KIT_LEVELS, default="instructions")
    import_skills = import_parser.add_mutually_exclusive_group()
    import_skills.add_argument(
        "--with-skills",
        dest="with_skills",
        action="store_true",
        help="Emit framework skill files after import (default).",
    )
    import_skills.add_argument(
        "--no-skills",
        dest="with_skills",
        action="store_false",
        help="Skip emitting skill files after import.",
    )
    import_parser.set_defaults(with_skills=True)

    specs = subcommands.add_parser("specs", help="Create or edit project specifications.")
    specs.add_argument("-C", "--project-dir", default=".")
    specs.add_argument("--refiner", choices=TOOL_IDS)
    specs.add_argument("--no-ai", action="store_true")
    specs.add_argument(
        "--no-interactive",
        action="store_true",
        help="Accepted for compatibility. Specs always publish without a prompt.",
    )

    validate = subcommands.add_parser("validate", help="Validate a project repository structure.")
    validate.add_argument("project_dir", nargs="?", default=".")

    ready = subcommands.add_parser(
        "ready",
        help="Check whether a project is ready for implementation task work.",
    )
    ready.add_argument("-C", "--project-dir", default=".")

    deps = subcommands.add_parser(
        "deps", help="Plan, install, or validate project-local dependencies."
    )
    deps_subcommands = deps.add_subparsers(dest="deps_command")
    for command, help_text in (
        ("plan", "Preview dependency managers, commands, and network access."),
        ("apply", "Run reviewed project-local dependency installation."),
        ("validate", "Validate dependency provenance and local environments."),
    ):
        deps_command = deps_subcommands.add_parser(command, help=help_text)
        deps_command.add_argument("-C", "--project-dir", default=".")
        if command == "apply":
            deps_command.add_argument("--allow-network", action="store_true")

    verify = subcommands.add_parser(
        "verify", help="Plan, run, or validate deterministic project checks."
    )
    verify_subcommands = verify.add_subparsers(dest="verify_command")
    for command, help_text in (
        ("plan", "Preview the verification commands that would run."),
        ("run", "Run verification commands and record the result."),
        ("validate", "Validate the latest verification evidence."),
    ):
        verify_command = verify_subcommands.add_parser(command, help=help_text)
        verify_command.add_argument("-C", "--project-dir", default=".")
        if command in {"plan", "run"}:
            verify_command.add_argument(
                "--profile", choices=("quick", "full"), default="quick"
            )
            verify_command.add_argument(
                "--check",
                action="append",
                choices=VERIFICATION_KINDS,
                default=[],
            )
        if command == "run":
            verify_command.add_argument(
                "--timeout",
                type=_positive_seconds,
                default=None,
                metavar="SECONDS",
                help=(
                    "Time limit for each command without its own `timeout` in "
                    "tool-policy.yaml (default 300)."
                ),
            )

    skills = subcommands.add_parser(
        "skills",
        help="Emit framework skill files for enabled tools.",
    )
    skills_subcommands = skills.add_subparsers(dest="skills_command")
    for command, help_text in (
        ("plan", "Preview skill files that would be created, kept, or conflict."),
        ("apply", "Emit skill files for enabled tools into the project."),
        ("validate", "Check that emitted skill files match framework templates."),
    ):
        skills_command = skills_subcommands.add_parser(command, help=help_text)
        skills_command.add_argument("-C", "--project-dir", default=".")
        skills_command.add_argument(
            "--skill",
            action="append",
            dest="only",
            metavar="NAME",
            help="Limit to specific skill names. Repeatable.",
        )
        if command == "apply":
            skills_command.add_argument(
                "--force",
                action="store_true",
                help="Overwrite conflicting files instead of preserving them.",
            )

    tools = subcommands.add_parser("tools", help="Configure project-local AI tool kits.")
    tools_subcommands = tools.add_subparsers(dest="tools_command")
    for command, help_text in (
        ("status", "Show the active policy and drift status."),
        ("configure", "Configure and review a project-local tool kit."),
        ("plan", "Preview provider files derived from the canonical policy."),
        ("apply", "Apply reviewed provider files without overwriting conflicts."),
        ("validate", "Validate policy, generated assets, and drift."),
    ):
        tools_command = tools_subcommands.add_parser(command, help=help_text)
        tools_command.add_argument("-C", "--project-dir", default=".")
        if command == "configure":
            tools_command.add_argument(
                "--no-interactive",
                action="store_true",
                help="Accepted for compatibility. Configure always publishes without a prompt.",
            )
            tools_command.add_argument("--level", choices=TOOL_KIT_LEVELS)
            tools_command.add_argument("--status", choices=("proposed", "approved"))
            tools_command.add_argument(
                "--tool",
                action="append",
                choices=TOOL_IDS,
                dest="tools",
                help="Replace enabled tools. Repeatable.",
            )
            tools_command.add_argument(
                "--protect-factory-assets",
                action=argparse.BooleanOptionalAction,
                default=None,
            )
            tools_command.add_argument(
                "--validate-on-stop",
                action=argparse.BooleanOptionalAction,
                default=None,
            )
            tools_command.add_argument(
                "--command",
                action="append",
                dest="command_specs",
                metavar="NAME=COMMAND",
                help="Merge a named validation command. Repeatable.",
            )

    configure_ids_parser(
        subcommands.add_parser(
            "ids", help="Check artifact ID uniqueness or print next free IDs."
        )
    )

    task = subcommands.add_parser("task", help="Create or move lifecycle task artifacts.")
    task_subcommands = task.add_subparsers(dest="task_command")
    task_create = task_subcommands.add_parser("create", help="Create a task artifact.")
    task_create.add_argument("task_id")
    task_create.add_argument("title")
    task_create.add_argument("--state", choices=TASK_STATES, default="backlog")
    task_create.add_argument("-C", "--project-dir", default=".")
    task_move = task_subcommands.add_parser("move", help="Move a task artifact.")
    task_move.add_argument("task_id")
    task_move.add_argument("state", choices=TASK_STATES)
    task_move.add_argument("-C", "--project-dir", default=".")
    task_archive = task_subcommands.add_parser(
        "archive", help="Move finished tasks out of the lifecycle folders into the archive."
    )
    task_archive.add_argument(
        "task_id", nargs="?", default=None, help="Archive one task ID or prefix."
    )
    task_archive.add_argument("--state", choices=TASK_STATES, default="done")
    task_archive.add_argument("-C", "--project-dir", default=".")

    gc = subcommands.add_parser(
        "gc",
        help="Archive old done tasks and delete timestamped verification runs.",
    )
    gc.add_argument("-C", "--project-dir", default=".")
    gc.add_argument(
        "--apply",
        action="store_true",
        help="Move archived tasks and delete verification runs. Default is a dry-run.",
    )
    gc.add_argument(
        "--keep",
        type=int,
        default=GC_DEFAULT_KEEP,
        metavar="N",
        help="Keep the N highest-numbered done tasks in the lifecycle folders (default 20).",
    )
    gc.add_argument(
        "--no-artifacts",
        dest="with_artifacts",
        action="store_false",
        help="Move tasks only; leave REV/QA/SUM artifacts in place.",
    )
    gc.add_argument(
        "--no-tasks",
        dest="with_tasks",
        action="store_false",
        help="Leave done tasks and their artifacts in place; only delete verification runs.",
    )
    gc.add_argument(
        "--no-runs",
        dest="with_runs",
        action="store_false",
        help="Keep verification/runs/; only archive done tasks.",
    )
    gc.set_defaults(with_artifacts=True, with_tasks=True, with_runs=True)
    return parser


def handle_init(args: argparse.Namespace) -> int:
    target_dir = Path(args.directory).resolve()
    factory_source = (
        Path(args.factory_source).resolve() if args.factory_source else framework_root()
    )
    validate_project_name(args.project_name)
    validate_factory_source(factory_source)
    if (target_dir / args.project_name).exists():
        raise FactoryError(f"Project path already exists: {target_dir / args.project_name}")
    tools_explicit = bool(args.tools)
    tools = list(dict.fromkeys(args.tools or TOOL_IDS))
    if args.intake_path:
        intake = load_intake_yaml(Path(args.intake_path).resolve())
    else:
        intake = ProjectIntake(project_name=args.project_name)
    overlay_cli_intake(
        intake,
        project_name=args.project_name,
        tools=tools,
        refiner=args.refiner,
        tool_kit_level=args.tool_kit,
        tools_explicit=tools_explicit,
        refiner_explicit=args.refiner is not None,
    )
    if args.refiner and args.refiner not in intake.tools:
        raise FactoryError("--refiner must also be enabled with --tool.")
    specs_source = None
    if args.specs_path:
        specs_source = read_text_file(
            Path(args.specs_path).resolve(), what="project specs"
        )
        merge_specs_into_intake(intake, specs_source)
    if args.preset:
        apply_project_preset(intake, args.preset)
    # --no-interactive is accepted and ignored. Init always publishes directly.
    del args.no_interactive

    if specs_source is not None and not intake.use_ai:
        specs_markdown = specs_source
    else:
        specs_markdown, warning = refine_with_feedback(
            intake,
            timeout=intake.refinement_timeout_seconds,
        )
        if warning:
            print(f"Warning: {warning}", file=sys.stderr)
            print("Using deterministic project specs draft.", file=sys.stderr)
        specs_markdown = review_refined_sections(intake, specs_markdown)

    project_dir, link_result = initialize_project(
        project_name=intake.project_name,
        target_dir=target_dir,
        factory_source=factory_source,
        intake=intake,
        force_copy=args.copy,
        specs_markdown=specs_markdown,
    )
    print(f"Created project: {project_dir}")
    print(f"Factory link: {link_result}")
    result = validate_project(project_dir)
    if result == 0 and getattr(args, "with_skills", False):
        apply_result = _apply_skills_after_init(project_dir, intake.tools)
        if apply_result is not None:
            print(apply_result)
    if result == 0:
        print("Next step:")
        print(
            "  complete .factory-state/tasks/backlog/TASK-0001-confirm-project-context.md"
        )
        print("  then convert specs (onboard-specs) and run `factory ready`")
        print("  before starting implementation tasks.")
    return result


def _apply_skills_after_init(
    project_dir: Path, enabled_tools: List[str]
) -> Optional[str]:
    factory_root = project_dir / ".factory"
    if not factory_root.is_dir():
        return "Skipping --with-skills: .factory framework root not found."
    try:
        plan = plan_skills(project_dir, factory_root, enabled_tools)
        result = apply_skills_plan(project_dir, plan)
    except SkillError as exc:
        return f"Skipping --with-skills: {exc}"
    lines = ["Applied framework skills:"]
    lines.append(render_apply_summary(result))
    return "\n".join(lines)


def handle_import(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    factory_source = (
        Path(args.factory_source).resolve() if args.factory_source else framework_root()
    )
    tools = list(dict.fromkeys(args.tools or TOOL_IDS))
    if args.refiner and args.refiner not in tools:
        raise FactoryError("--refiner must also be enabled with --tool.")
    intake = ProjectIntake(
        project_name=project_dir.name,
        tools=tools,
        refiner=args.refiner,
        tool_kit_level=args.tool_kit,
    )
    plan = plan_import(project_dir, factory_source, intake)
    print(plan.render())
    if plan.invalid:
        return 1
    # --no-interactive is accepted and ignored. Apply still requires --apply.
    del args.no_interactive
    if not args.apply:
        print("Import preview complete; no files were changed.")
        return 0
    link_result = apply_import(
        plan,
        factory_source,
        force_copy=args.copy,
    )
    print(f"Import applied. Factory link: {link_result}")
    result = validate_project(project_dir)
    if result == 0 and getattr(args, "with_skills", False):
        apply_result = _apply_skills_after_init(project_dir, intake.tools)
        if apply_result is not None:
            print(apply_result)
    return result


def handle_ready(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        raise FactoryError(f"Project directory does not exist: {project_dir}")
    report = inspect_readiness(project_dir)
    print(render_readiness(report))
    return 0 if report.ready else 1


def handle_specs(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        raise FactoryError(f"Project directory does not exist: {project_dir}")
    intake = load_intake(project_dir)
    config = load_config(project_dir)
    intake.tools = list(config.enabled_tools)
    intake.refiner = args.refiner or config.default_refiner
    intake.use_ai = bool(intake.refiner) and not args.no_ai
    intake.refinement_timeout_seconds = config.refinement_timeout_seconds
    intake.refinement = {}
    # --no-interactive is accepted and ignored. Specs always publish directly.
    del args.no_interactive
    markdown, warning = refine_with_feedback(
        intake,
        timeout=intake.refinement_timeout_seconds,
    )
    if warning:
        print(f"Warning: {warning}", file=sys.stderr)
        print("Using deterministic project specs draft.", file=sys.stderr)
    markdown = review_refined_sections(intake, markdown)
    publish_specs(project_dir, intake, markdown, config=config)
    print(f"Published project specs: {project_dir / 'project-specs.md'}")
    return 0


def handle_skills(args: argparse.Namespace) -> int:
    if not args.skills_command:
        raise SkillError("Choose a skills command: plan, apply, or validate.")
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        raise SkillError(f"Project directory does not exist: {project_dir}")
    factory_root = project_dir / ".factory"
    if not factory_root.is_dir():
        raise SkillError(
            f"Framework root not found: {factory_root}. Run this inside a factory project."
        )
    config = load_config(project_dir)
    only = list(dict.fromkeys(args.only)) if args.only else None
    plan = plan_skills(project_dir, factory_root, config.enabled_tools, only=only)

    if args.skills_command == "plan":
        print(plan.render())
        return 0
    if args.skills_command == "validate":
        if not plan.entries:
            print("No skill templates found in .factory/templates/skills/.")
            return 0
        drifts = plan.conflicts
        missing = plan.creates
        if not drifts and not missing and not plan.updates:
            print(f"Skills validation passed: {len(plan.keeps)} in sync.")
            return 0
        print("Skills validation failed:")
        for entry in missing:
            print(f"  missing  {entry.asset.path}")
        for entry in plan.updates:
            print(f"  update   {entry.asset.path}  (run factory skills apply)")
        for entry in drifts:
            print(f"  drift    {entry.asset.path}  ({entry.reason})")
        return 1
    if args.skills_command == "apply":
        result = apply_skills_plan(project_dir, plan, force=args.force)
        print(render_apply_summary(result))
        return 1 if result.had_conflicts else 0
    raise SkillError(f"Unknown skills command: {args.skills_command}")


def configure_policy_from_args(project_dir: Path, args: argparse.Namespace):
    """Build a tool policy from the current file (or defaults) plus CLI flags."""
    try:
        base = load_tool_policy(project_dir)
    except ValueError:
        config = load_config(project_dir)
        tools = list(args.tools) if args.tools else list(config.enabled_tools)
        base = default_tool_policy(tools, args.level or "instructions")
    commands = None
    if args.command_specs:
        try:
            commands = dict(
                parse_command_spec(item) for item in args.command_specs
            )
        except ValueError as exc:
            raise FactoryError(str(exc)) from exc
    try:
        return overlay_tool_policy(
            base,
            level=args.level,
            status=args.status,
            enabled_tools=args.tools,
            protect_factory_assets=args.protect_factory_assets,
            validate_on_stop=args.validate_on_stop,
            commands=commands,
        )
    except ValueError as exc:
        raise FactoryError(str(exc)) from exc


def handle_tools(args: argparse.Namespace) -> int:
    if not args.tools_command:
        raise FactoryError("Choose a tools command: status, configure, plan, apply, or validate.")
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        raise FactoryError(f"Project directory does not exist: {project_dir}")

    if args.tools_command == "configure":
        # --no-interactive is accepted and ignored.
        del args.no_interactive
        policy = configure_policy_from_args(project_dir, args)
        plan = plan_tooling(project_dir, policy)
        print(plan.render().replace("Import plan:", "Tooling plan:", 1))
        return publish_tooling_plan(project_dir, policy, plan, None)

    try:
        policy = load_tool_policy(project_dir)
    except (OSError, ValueError) as exc:
        raise FactoryError(str(exc)) from exc

    if args.tools_command == "status":
        print(render_tooling_status(project_dir, policy))
        errors, _ = tooling_problems(project_dir)
        return 1 if errors else 0
    if args.tools_command == "validate":
        errors, warnings = tooling_problems(project_dir)
        if errors:
            print("Tooling validation failed:")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"Tooling validation passed: {project_dir}")
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        return 1 if errors else 0

    plan = plan_tooling(project_dir, policy)
    print(plan.render().replace("Import plan:", "Tooling plan:", 1))
    if args.tools_command == "plan":
        return 1 if plan.invalid else 0
    if plan.invalid:
        return 1
    return publish_tooling_plan(project_dir, policy, plan, None)


def handle_dependencies(args: argparse.Namespace) -> int:
    if not args.deps_command:
        raise FactoryError("Choose a deps command: plan, apply, or validate.")
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        raise FactoryError(f"Project directory does not exist: {project_dir}")
    if args.deps_command == "validate":
        errors, warnings = dependency_problems(
            project_dir,
            require_state=True,
            check_integrity=True,
        )
        if errors:
            print("Dependency validation failed:")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"Dependency validation passed: {project_dir}")
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        return 1 if errors else 0

    plan = create_dependency_plan(project_dir)
    print(plan.render())
    if args.deps_command == "plan":
        return 0 if plan.ready else 1
    return apply_dependency_plan_with_review(
        plan,
        allow_network=args.allow_network,
    )


def apply_dependency_plan_with_review(
    plan: DependencyPlan,
    *,
    allow_network: bool,
) -> int:
    try:
        print("Installing project-local dependencies…", file=sys.stderr)
        apply_dependency_plan(plan, allow_network=allow_network)
    except DependencyError as exc:
        raise FactoryError(str(exc)) from exc
    print(f"Dependencies installed: {plan.project_dir}")
    return 0


def _positive_seconds(value: str) -> int:
    try:
        seconds = int(value)
    except ValueError:
        seconds = 0
    if seconds <= 0:
        raise argparse.ArgumentTypeError("must be a whole number of seconds above 0")
    return seconds


def handle_verification(args: argparse.Namespace) -> int:
    if not args.verify_command:
        raise FactoryError("Choose a verify command: plan, run, or validate.")
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        raise FactoryError(f"Project directory does not exist: {project_dir}")
    if args.verify_command == "validate":
        errors, warnings = verification_problems(project_dir, require_state=True)
        if errors:
            print("Verification validation failed:")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"Verification validation passed: {project_dir}")
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        return 1 if errors else 0

    plan = create_verification_plan(
        project_dir,
        profile=args.profile,
        selected_kinds=args.check,
    )
    print(plan.render())
    if args.verify_command == "plan":
        return 0 if plan.ready else 1
    if not plan.ready:
        return 1
    print("Running deterministic project verification…", file=sys.stderr)
    results = run_verification_plan(plan, timeout_seconds=args.timeout)
    for result in results:
        print(
            f"  {result.status.upper():6} {result.check.check_id} "
            f"({result.duration_seconds:.2f}s)"
        )
        if result.status == "failed":
            detail = result.output or result.error or "unknown failure"
            print(f"    {detail[-2000:]}")
    failed = [result for result in results if result.status != "passed"]
    if failed:
        print(f"Project verification failed: {len(failed)} check(s).")
        return 1
    print(f"Project verification passed: {project_dir}")
    return 0


def publish_tooling_plan(
    project_dir: Path,
    policy,
    plan,
    resolutions: Optional[dict],
) -> int:
    try:
        unresolved = apply_tooling_plan(project_dir, policy, plan, resolutions)
    except ValueError as exc:
        raise FactoryError(str(exc)) from exc
    if unresolved:
        print("Applied safe tooling changes; existing provider files were preserved.")
        print("Resolve proposals before enabling the complete kit:")
        for path in unresolved:
            print(f"  - {path}")
        return 1
    print(f"Applied {policy.level} tool kit: {project_dir}")
    if (
        policy.active
        and "codex" in policy.enabled_tools
        and (policy.protect_factory_assets or policy.validate_on_stop)
    ):
        print("Codex next step: trust the project, then review project hooks with `/hooks`.")
    errors, warnings = tooling_problems(project_dir)
    for warning in warnings:
        print(f"Warning: {warning}", file=sys.stderr)
    return 1 if errors else 0


def refine_with_feedback(
    intake: ProjectIntake,
    timeout: int,
) -> Tuple[str, Optional[str]]:
    progress = None
    if intake.use_ai and intake.refiner:
        print(f"Refining project specs with {intake.refiner}…", file=sys.stderr)

        def report(message: str) -> None:
            print(f"  {message}", file=sys.stderr)

        progress = report
    return refine_specs(intake, timeout=timeout, progress=progress)


def review_refined_sections(
    intake: ProjectIntake,
    refined_markdown: str,
) -> str:
    """Apply in-scope AI section changes without a review prompt."""
    if intake.refinement.get("status") != "refined":
        return refined_markdown
    deterministic = render_project_specs(intake)
    target_headings = refinement_headings(intake.refinement_sections)
    allowed = target_headings if target_headings else None
    changed = changed_sections(deterministic, refined_markdown, allowed)

    if not changed:
        selected_markdown = deterministic
        accepted: List[str] = []
        rejected: List[str] = []
    elif target_headings:
        selected_markdown = merge_sections(deterministic, refined_markdown, changed)
        accepted = list(changed)
        rejected = []
    else:
        selected_markdown = refined_markdown
        accepted = list(changed)
        rejected = []

    intake.refinement["accepted_sections"] = accepted
    intake.refinement["rejected_sections"] = rejected
    intake.refinement["output_sha256"] = sha256(
        selected_markdown.encode("utf-8")
    ).hexdigest()
    return selected_markdown


if __name__ == "__main__":
    raise SystemExit(main())
