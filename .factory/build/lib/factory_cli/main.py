from __future__ import annotations

import argparse
import difflib
import shutil
import sys
from hashlib import sha256
from pathlib import Path
from typing import List, Optional, Tuple

from .adapters import detect_tools
from .clarification import load_clarification, resolve_clarification, save_clarification
from .configuration import (
    ConfigurationError,
    ConfigurationOutput,
    ConfigurationPlan,
    apply_configuration_plan,
    configuration_problems,
    create_configuration_plan,
)
from .constants import (
    GC_DEFAULT_KEEP,
    INTAKE_ROOT,
    PROJECT_PRESET_IDS,
    TASK_STATES,
    TOOL_IDS,
    TOOL_KIT_LEVELS,
    TOOL_POLICY_PATH,
    USAGE_SCOPES,
)
from . import metrics, registry
from .storage import StoreError, open_store
from .dependencies import (
    DependencyError,
    DependencyPlan,
    apply_dependency_plan,
    create_dependency_plan,
    dependency_problems,
    render_dependency_review,
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
    build_config,
    framework_root,
    initialize_project,
    load_config,
    load_intake,
    plan_import,
    publish_specs,
    refine_specs,
    render_project_files,
    validate_factory_source,
    validate_project_name,
)
from .renderers import render_confidence_review, render_project_specs
from .scaffold import (
    ScaffoldAction,
    ScaffoldError,
    ScaffoldOutput,
    ScaffoldPublishPlan,
    apply_scaffold_plan,
    create_scaffold_plan,
    default_scaffold_registry,
    scaffold_problems,
    stage_scaffold,
)
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
from .tui import (
    BoardApp,
    ClarificationApp,
    DashboardApp,
    DraftReviewApp,
    ImportReviewApp,
    ProjectsApp,
    ProjectWizardApp,
    RefinementConfigApp,
    RefinementApp,
    ReviewApp,
    SectionReviewApp,
    ScaffoldReviewApp,
    ToolingConfigApp,
    ToolingReviewApp,
)
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
    render_verification_review,
    run_verification_plan,
    verification_problems,
)
from .orchestrator import (
    OrchestratorError,
    apply_orchestrator_plan,
    cleanup_worktrees,
    create_orchestrator_plan,
    load_state,
    orchestrator_problems,
    render_orchestrator_review,
)
from .validation import validate_project


def main(argv: Optional[List[str]] = None) -> int:
    parser = build_parser()
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    if not raw_argv and is_interactive():
        # Bare `factory` in a TTY drops into the interactive shell; keep the
        # help path for non-interactive contexts below.
        raw_argv = ["shell"]
    args = parser.parse_args(raw_argv)
    try:
        if args.command == "shell":
            return handle_shell(args, parser)
        if args.command == "init":
            return handle_init(args)
        if args.command == "import":
            return handle_import(args)
        if args.command == "specs":
            return handle_specs(args)
        if args.command == "clarify":
            return handle_clarify(args)
        if args.command == "validate":
            return validate_project(Path(args.project_dir).resolve())
        if args.command == "ready":
            return handle_ready(args)
        if args.command == "tools":
            return handle_tools(args)
        if args.command == "scaffold":
            return handle_scaffold(args)
        if args.command == "deps":
            return handle_dependencies(args)
        if args.command == "verify":
            return handle_verification(args)
        if args.command == "stack":
            return handle_stack_configuration(args)
        if args.command == "skills":
            return handle_skills(args)
        if args.command == "orchestrate":
            return handle_orchestrate(args)
        if args.command == "projects":
            return handle_projects(args)
        if args.command == "board":
            return handle_board(args)
        if args.command == "usage":
            return handle_usage(args)
        if args.command == "budget":
            return handle_budget(args)
        if args.command == "dashboard":
            return handle_dashboard(args)
        if args.command == "ids":
            return run_ids(args)
        if args.command == "gc":
            return run_gc(
                project_dir=Path(args.project_dir).resolve(),
                keep=args.keep,
                with_artifacts=args.with_artifacts,
                apply=args.apply,
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
        ConfigurationError,
        FactoryError,
        DependencyError,
        VerificationError,
        OrchestratorError,
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
    specs.add_argument("--no-interactive", action="store_true")

    clarify = subcommands.add_parser("clarify", help="Answer one clarification artifact.")
    clarify.add_argument("identifier", help="Clarification ID or artifact path.")
    clarify.add_argument("-C", "--project-dir", default=".")

    validate = subcommands.add_parser("validate", help="Validate a project repository structure.")
    validate.add_argument("project_dir", nargs="?", default=".")

    ready = subcommands.add_parser(
        "ready",
        help="Check whether a project is ready for implementation task work.",
    )
    ready.add_argument("-C", "--project-dir", default=".")

    scaffold = subcommands.add_parser(
        "scaffold", help="Plan, apply, or validate source scaffolding."
    )
    scaffold_subcommands = scaffold.add_subparsers(dest="scaffold_command")
    for command, help_text in (
        ("plan", "Preview adapters, commands, and expected source paths."),
        ("apply", "Run approved adapters in staging and publish reviewed output."),
        ("validate", "Validate managed scaffold output and source decisions."),
    ):
        scaffold_command = scaffold_subcommands.add_parser(command, help=help_text)
        scaffold_command.add_argument("-C", "--project-dir", default=".")
        if command == "apply":
            dependency_mode = scaffold_command.add_mutually_exclusive_group()
            dependency_mode.add_argument("--with-deps", action="store_true")
            dependency_mode.add_argument("--skip-deps", action="store_true")
            scaffold_command.add_argument("--allow-network", action="store_true")

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
        ("plan", "Preview deterministic project validation checks."),
        ("run", "Run reviewed checks and record verification evidence."),
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
                choices=("check", "test", "lint", "typecheck", "build"),
                default=[],
            )

    stack = subcommands.add_parser(
        "stack", help="Plan, apply, or validate approved stack configuration."
    )
    stack_subcommands = stack.add_subparsers(dest="stack_command")
    for command, help_text in (
        ("plan", "Preview configuration derived from Approved stack choices."),
        ("apply", "Publish reviewed stack configuration without overwriting conflicts."),
        ("validate", "Validate managed stack configuration and decision drift."),
    ):
        stack_command = stack_subcommands.add_parser(command, help=help_text)
        stack_command.add_argument("-C", "--project-dir", default=".")

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
                help="Write policy from flags (or the current/default policy) without the TUI.",
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

    orchestrate = subcommands.add_parser(
        "orchestrate",
        help="Dispatch todo tasks to multiple AI tools in parallel git worktrees.",
    )
    orchestrate_subcommands = orchestrate.add_subparsers(dest="orchestrate_command")
    for command, help_text in (
        ("plan", "Preview task-to-tool assignments and worktree layout."),
        ("run", "Create worktrees, write briefs, and move tasks to doing."),
        ("status", "Show recorded orchestration worktrees and tools."),
        ("validate", "Validate orchestration state against live worktrees."),
        ("cleanup", "Remove clean factory-created worktrees and prune state."),
    ):
        orchestrate_command = orchestrate_subcommands.add_parser(command, help=help_text)
        orchestrate_command.add_argument("-C", "--project-dir", default=".")
        orchestrate_command.add_argument(
            "--tool", action="append", choices=TOOL_IDS, dest="tools"
        )
        if command in {"plan", "run"}:
            orchestrate_command.add_argument("--max-parallel", type=int, default=None)
        if command == "run":
            orchestrate_command.add_argument("--launch", action="store_true")
            orchestrate_command.add_argument("--yes", action="store_true")
        if command == "cleanup":
            orchestrate_command.add_argument("--force", action="store_true")

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
        "archive", help="Move finished tasks out of the board into the archive."
    )
    task_archive.add_argument(
        "task_id", nargs="?", default=None, help="Archive one task ID or prefix."
    )
    task_archive.add_argument("--state", choices=TASK_STATES, default="done")
    task_archive.add_argument("-C", "--project-dir", default=".")

    gc = subcommands.add_parser(
        "gc",
        help="Archive old done tasks and companion REV/QA/SUM artifacts.",
    )
    gc.add_argument("-C", "--project-dir", default=".")
    gc.add_argument(
        "--apply",
        action="store_true",
        help="Write the archive. Default is a dry-run inventory and plan.",
    )
    gc.add_argument(
        "--keep",
        type=int,
        default=GC_DEFAULT_KEEP,
        metavar="N",
        help="Keep the N highest-numbered done tasks on the board (default 20).",
    )
    gc.add_argument(
        "--no-artifacts",
        dest="with_artifacts",
        action="store_false",
        help="Move tasks only; leave REV/QA/SUM artifacts in place.",
    )
    gc.set_defaults(with_artifacts=True)

    projects = subcommands.add_parser(
        "projects", help="Register and open factory projects."
    )
    projects_subcommands = projects.add_subparsers(dest="projects_command")
    projects_subcommands.add_parser("list", help="List registered projects.")
    projects_add = projects_subcommands.add_parser("add", help="Register a project.")
    projects_add.add_argument("path", nargs="?", default=".")
    projects_add.add_argument("--name")
    projects_remove = projects_subcommands.add_parser(
        "remove", help="Unregister a project by name."
    )
    projects_remove.add_argument("name")

    board = subcommands.add_parser("board", help="Open the Kanban task board (TUI).")
    board.add_argument("-C", "--project-dir", default=".")
    board.add_argument("--project", help="Open a registered project by name.")

    usage = subcommands.add_parser(
        "usage", help="Record and report token/cost usage metrics."
    )
    usage_subcommands = usage.add_subparsers(dest="usage_command")
    usage_record = usage_subcommands.add_parser("record", help="Record a usage entry.")
    usage_record.add_argument("-C", "--project-dir", default=".")
    usage_record.add_argument("--scope", choices=USAGE_SCOPES, required=True)
    usage_record.add_argument("--ref", required=True)
    usage_record.add_argument("--tool", default="", dest="tool_id")
    usage_record.add_argument("--in", type=int, default=0, dest="input_tokens")
    usage_record.add_argument("--out", type=int, default=0, dest="output_tokens")
    usage_record.add_argument("--cost", type=float, default=0.0, dest="cost_usd")
    usage_record.add_argument("--note")
    usage_list = usage_subcommands.add_parser("list", help="Summarize usage.")
    usage_list.add_argument("-C", "--project-dir", default=".")
    usage_list.add_argument(
        "--by", choices=("ref", "tool", "scope", "budget"), default="ref"
    )
    usage_import = usage_subcommands.add_parser(
        "import", help="Bulk-import usage records from a JSONL or CSV file."
    )
    usage_import.add_argument("path", help="Path to a .jsonl/.json or .csv file.")
    usage_import.add_argument("-C", "--project-dir", default=".")
    usage_capture = usage_subcommands.add_parser(
        "capture",
        help="Parse a coding tool's JSON output and record one usage entry.",
    )
    usage_capture.add_argument("--tool", required=True, dest="tool_id")
    usage_capture.add_argument("--ref", required=True)
    usage_capture.add_argument("--scope", choices=USAGE_SCOPES, default="task")
    usage_capture.add_argument(
        "--from", dest="source", default=None, help="Read output from a file (else stdin)."
    )
    usage_capture.add_argument("--note")
    usage_capture.add_argument("-C", "--project-dir", default=".")

    budget = subcommands.add_parser("budget", help="Manage token budgets.")
    budget_subcommands = budget.add_subparsers(dest="budget_command")
    budget_list = budget_subcommands.add_parser(
        "list", help="List budgets and current usage."
    )
    budget_list.add_argument("-C", "--project-dir", default=".")
    budget_set = budget_subcommands.add_parser("set", help="Set a token budget.")
    budget_set.add_argument("key", help="e.g. task:TASK-0001 or agent:developer")
    budget_set.add_argument("limit", type=int)
    budget_set.add_argument("-C", "--project-dir", default=".")
    budget_remove = budget_subcommands.add_parser("remove", help="Remove a budget.")
    budget_remove.add_argument("key")
    budget_remove.add_argument("-C", "--project-dir", default=".")

    dashboard = subcommands.add_parser(
        "dashboard", help="Open the metrics dashboard (TUI)."
    )
    dashboard.add_argument("-C", "--project-dir", default=".")
    dashboard.add_argument("--project", help="Open a registered project by name.")

    shell = subcommands.add_parser(
        "shell",
        help="Open the interactive REPL (discover and launch commands).",
    )
    shell.add_argument(
        "-C",
        "--project-dir",
        default=None,
        help="Pre-select a project by path.",
    )
    shell.add_argument(
        "--project",
        default=None,
        help="Pre-select a registered project by name.",
    )
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
    tool_availability = detect_tools()
    git_available = shutil.which("git") is not None
    interactive = is_interactive() and not args.no_interactive
    if interactive:
        result = ProjectWizardApp(intake, tool_availability=tool_availability).run()
        if result is None:
            print("Project initialization cancelled; no files were created.")
            return 0
        intake = result
        if not configure_refinement_after_draft(
            intake,
            tool_availability,
        ):
            print("Project initialization cancelled; no files were created.")
            return 0

    preserve_owner_specs = (
        specs_source is not None and not interactive and not intake.use_ai
    )
    if preserve_owner_specs:
        specs_markdown = specs_source
    else:
        refinement = refine_with_feedback(
            intake,
            timeout=intake.refinement_timeout_seconds,
            interactive=interactive,
        )
        if refinement is None:
            print("Project initialization cancelled; no files were created.")
            return 0
        specs_markdown, warning = refinement
        if warning:
            print(f"Warning: {warning}", file=sys.stderr)
            print("Using deterministic project specs draft.", file=sys.stderr)
        specs_markdown = review_refined_sections(intake, specs_markdown, interactive)

    if interactive:
        preview_link = "copy" if args.copy or not git_available else "submodule"
        config = build_config(intake, link_mode=preview_link)
        bundle = render_project_files(intake, config, specs_markdown=specs_markdown)
        review = render_init_review(
            bundle,
            intake,
            specs_markdown,
            render_project_specs(intake),
            (
                "copy"
                if args.copy
                else "submodule with copy fallback"
                if git_available
                else "copy (Git CLI not found)"
            ),
        )
        if not ReviewApp(review, accept_label="Create project").run():
            print("Project initialization cancelled; no files were created.")
            return 0

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
    try:
        registry.add_project(project_dir)
        print(f"Registered project: {project_dir.name}")
    except FactoryError as exc:
        print(f"Warning: could not register project: {exc}", file=sys.stderr)
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
    interactive = is_interactive() and not args.no_interactive
    should_apply = args.apply
    conflict_resolutions = None
    if interactive:
        import_review = ImportReviewApp(plan, project_dir, render_import_review(plan, project_dir))
        conflict_resolutions = import_review.run()
        should_apply = conflict_resolutions is not None
    if not should_apply:
        print("Import preview complete; no files were changed.")
        return 0
    link_result = apply_import(
        plan,
        factory_source,
        force_copy=args.copy,
        conflict_resolutions=conflict_resolutions,
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
    interactive = is_interactive() and not args.no_interactive
    if interactive:
        intake_path = project_dir / INTAKE_ROOT / "project-specs-input.yaml"
        tool_availability = detect_tools()
        wizard = ProjectWizardApp(
            intake,
            save_path=intake_path,
            tool_availability=tool_availability,
        )
        result = wizard.run()
        if result is None:
            if wizard.saved:
                print(f"Specs draft saved: {intake_path}")
                return 0
            print("Specs editing cancelled; no files were changed.")
            return 0
        intake = result
        if not configure_refinement_after_draft(
            intake,
            tool_availability,
            allow_ai=not args.no_ai,
        ):
            print("Specs editing cancelled; no files were changed.")
            return 0
    refinement = refine_with_feedback(
        intake,
        timeout=intake.refinement_timeout_seconds,
        interactive=interactive,
    )
    if refinement is None:
        print("Specs refinement cancelled; no files were changed.")
        return 0
    markdown, warning = refinement
    if warning:
        print(f"Warning: {warning}", file=sys.stderr)
        print("Using deterministic project specs draft.", file=sys.stderr)
    markdown = review_refined_sections(intake, markdown, interactive)
    previous_markdown = ""
    specs_path = project_dir / "project-specs.md"
    if specs_path.is_file():
        previous_markdown = specs_path.read_text(encoding="utf-8")
    specs_review = (
        "# Project specs review\n\n"
        + render_confidence_review(intake, heading_level=2)
        + "\n"
        + render_diff(
            previous_markdown,
            markdown,
            "current/project-specs.md",
            "proposed/project-specs.md",
        )
        + "\n\n## Proposed specification\n\n"
        + markdown
    )
    if interactive and not ReviewApp(specs_review, accept_label="Publish specs").run():
        print("Specs editing cancelled; no files were changed.")
        return 0
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
        if not drifts and not missing:
            print(f"Skills validation passed: {len(plan.keeps)} in sync.")
            return 0
        print("Skills validation failed:")
        for entry in missing:
            print(f"  missing  {entry.asset.path}")
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
        if args.no_interactive or not is_interactive():
            if not args.no_interactive:
                raise FactoryError(
                    "factory tools configure requires an interactive terminal. "
                    "Pass --no-interactive to apply flags or the current/default policy."
                )
            policy = configure_policy_from_args(project_dir, args)
            plan = plan_tooling(project_dir, policy)
            print(plan.render().replace("Import plan:", "Tooling plan:", 1))
            return publish_tooling_plan(project_dir, policy, plan, None)
        try:
            policy = load_tool_policy(project_dir)
        except ValueError:
            config = load_config(project_dir)
            policy = default_tool_policy(config.enabled_tools)
        configured = ToolingConfigApp(policy).run()
        if configured is None:
            print("Tool kit configuration cancelled; no files were changed.")
            return 0
        plan = plan_tooling(project_dir, configured)
        review = render_tooling_review(project_dir, configured.to_yaml(), plan)
        resolutions = ToolingReviewApp(plan, review).run()
        if resolutions is None:
            print("Tool kit configuration cancelled; no files were changed.")
            return 0
        return publish_tooling_plan(project_dir, configured, plan, resolutions)

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
    resolutions = None
    if is_interactive():
        resolutions = ToolingReviewApp(
            plan,
            render_tooling_review(project_dir, policy.to_yaml(), plan),
        ).run()
        if resolutions is None:
            print("Tool kit apply cancelled; no files were changed.")
            return 0
    return publish_tooling_plan(project_dir, policy, plan, resolutions)


def handle_scaffold(args: argparse.Namespace) -> int:
    if not args.scaffold_command:
        raise FactoryError("Choose a scaffold command: plan, apply, or validate.")
    if (
        args.scaffold_command == "apply"
        and args.allow_network
        and not args.with_deps
    ):
        raise FactoryError("--allow-network requires --with-deps for scaffold apply.")
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        raise FactoryError(f"Project directory does not exist: {project_dir}")

    if args.scaffold_command == "validate":
        errors, warnings = scaffold_problems(project_dir)
        if errors:
            print("Scaffold validation failed:")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"Scaffold validation passed: {project_dir}")
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        return 1 if errors else 0

    registry = default_scaffold_registry()
    try:
        plan = create_scaffold_plan(project_dir, registry)
    except ScaffoldError as exc:
        raise FactoryError(str(exc)) from exc
    print(plan.render())
    if args.scaffold_command == "plan":
        return 0 if plan.ready else 1
    if not plan.ready:
        return 1

    print("Running scaffold adapters in an isolated staging directory…", file=sys.stderr)
    try:
        publish_plan = stage_scaffold(plan, registry)
    except ScaffoldError as exc:
        raise FactoryError(str(exc)) from exc
    print(publish_plan.render())
    resolutions = None
    if is_interactive():
        review = render_scaffold_review(publish_plan)
        resolutions = ScaffoldReviewApp(publish_plan, review).run()
        if resolutions is None:
            print("Scaffold apply cancelled; no project source files were changed.")
            return 0
    try:
        unresolved = apply_scaffold_plan(publish_plan, resolutions)
    except ScaffoldError as exc:
        raise FactoryError(str(exc)) from exc
    if unresolved:
        print("Applied non-conflicting scaffold output; existing source was preserved.")
        print("Resolve scaffold proposals:")
        for path in unresolved:
            print(f"  - {path}")
        return 1
    print(f"Scaffold applied: {project_dir}")
    if args.skip_deps:
        print("Dependency installation skipped by owner request.")
        return 0
    if args.with_deps:
        return apply_dependencies_with_review(
            project_dir,
            allow_network=args.allow_network,
            source_already_published=True,
            require_install=True,
        )
    if is_interactive():
        return apply_dependencies_with_review(
            project_dir,
            allow_network=False,
            source_already_published=True,
            require_install=False,
        )
    return 0


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
        source_already_published=False,
    )


def apply_dependencies_with_review(
    project_dir: Path,
    *,
    allow_network: bool,
    source_already_published: bool,
    require_install: bool,
) -> int:
    plan = create_dependency_plan(project_dir)
    print(plan.render())
    if not plan.ready:
        if require_install:
            return 1
        print("Dependency phase skipped because its plan is not ready.")
        return 0
    return apply_dependency_plan_with_review(
        plan,
        allow_network=allow_network,
        source_already_published=source_already_published,
    )


def apply_dependency_plan_with_review(
    plan: DependencyPlan,
    *,
    allow_network: bool,
    source_already_published: bool,
) -> int:
    if is_interactive():
        accepted = ReviewApp(
            render_dependency_review(plan),
            accept_label="Install dependencies",
        ).run()
        if not accepted:
            print("Dependency installation skipped; source files were preserved.")
            return 0
        allow_network = True
    try:
        print("Installing project-local dependencies…", file=sys.stderr)
        apply_dependency_plan(plan, allow_network=allow_network)
    except DependencyError as exc:
        prefix = "Source scaffold was published, but " if source_already_published else ""
        raise FactoryError(prefix + str(exc)) from exc
    print(f"Dependencies installed: {plan.project_dir}")
    return 0


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
    if is_interactive():
        accepted = ReviewApp(
            render_verification_review(plan),
            accept_label="Run verification",
        ).run()
        if not accepted:
            print("Project verification cancelled; no checks were run.")
            return 0
    print("Running deterministic project verification…", file=sys.stderr)
    results = run_verification_plan(plan)
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


def handle_orchestrate(args: argparse.Namespace) -> int:
    if not args.orchestrate_command:
        raise FactoryError(
            "Choose an orchestrate command: plan, run, status, validate, or cleanup."
        )
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        raise FactoryError(f"Project directory does not exist: {project_dir}")

    if args.orchestrate_command == "status":
        records = load_state(project_dir)
        if not records:
            print(f"No active orchestration recorded: {project_dir}")
            return 0
        for record in records:
            print(f"  {record.status.upper():9} {record.task_id} -> {record.tool_id}")
            print(f"    branch:   {record.branch}")
            print(f"    worktree: {record.worktree_path}")
            if record.launch_command:
                print(f"    launch:   {record.launch_command}")
        return 0

    if args.orchestrate_command == "validate":
        errors, warnings = orchestrator_problems(project_dir, require_state=True)
        if errors:
            print("Orchestration validation failed:")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"Orchestration validation passed: {project_dir}")
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        return 1 if errors else 0

    if args.orchestrate_command == "cleanup":
        removed, skipped = cleanup_worktrees(project_dir, force=args.force)
        for task_id in removed:
            print(f"  removed   {task_id}")
        for message in skipped:
            print(f"  skipped   {message}")
        if not removed and not skipped:
            print("No orchestration worktrees to clean.")
        return 0

    plan = create_orchestrator_plan(
        project_dir,
        tools=args.tools,
        max_parallel=args.max_parallel,
    )
    print(plan.render())
    if args.orchestrate_command == "plan":
        return 0 if plan.ready else 1
    if not plan.ready:
        return 1
    if is_interactive() and not args.yes:
        accepted = ReviewApp(
            render_orchestrator_review(plan),
            accept_label="Create worktrees",
        ).run()
        if not accepted:
            print("Orchestration cancelled; no worktrees were created.")
            return 0
    print("Preparing task worktrees…", file=sys.stderr)
    records = apply_orchestrator_plan(
        plan,
        launch=args.launch,
        max_parallel=args.max_parallel,
    )
    for record in records:
        print(f"  {record.status.upper():9} {record.task_id} -> {record.tool_id}")
        print(f"    worktree: {record.worktree_path}")
        if record.launch_command and not args.launch:
            print(f"    run:      (cd {record.worktree_path} && {record.launch_command})")
    incomplete = project_dir / ".factory-state/orchestration/INCOMPLETE"
    if incomplete.exists():
        print(
            "Some assignments failed; see "
            ".factory-state/orchestration/INCOMPLETE and rerun.",
            file=sys.stderr,
        )
        return 1
    print(f"Prepared {len(records)} task worktree(s): {project_dir}")
    return 0


def resolve_project_dir(args: argparse.Namespace) -> Path:
    name = getattr(args, "project", None)
    if name:
        project_dir = registry.resolve_project(name).resolve()
    else:
        project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        raise FactoryError(f"Project directory does not exist: {project_dir}")
    return project_dir


def handle_projects(args: argparse.Namespace) -> int:
    command = getattr(args, "projects_command", None)
    if command == "add":
        entry = registry.add_project(Path(args.path).resolve(), name=args.name)
        print(f"Registered project: {entry.name} -> {entry.path}")
        return 0
    if command == "remove":
        if registry.remove_project(args.name):
            print(f"Unregistered project: {args.name}")
            return 0
        raise FactoryError(f"No registered project named: {args.name}")

    entries = registry.list_projects()
    if command == "list":
        if not entries:
            print("No projects registered. Run `factory init` or `factory projects add`.")
            return 0
        for entry in entries:
            print(f"  {entry.name}\t{entry.path}")
        return 0

    # No subcommand: interactive picker that opens the board, else list.
    if not is_interactive():
        return handle_projects(argparse.Namespace(projects_command="list"))
    selected = ProjectsApp(entries).run()
    if selected is None:
        return 0
    name, action = selected
    project_dir = registry.resolve_project(name).resolve()
    if action == "dashboard":
        return open_dashboard(project_dir)
    return open_board(project_dir)


def open_board(project_dir: Path) -> int:
    config = load_config(project_dir)
    store = open_store(project_dir, config)
    assignments = {}
    try:
        for record in load_state(project_dir):
            if record.status in {"prepared", "launched"}:
                assignments[record.task_id] = (record.tool_id, record.created_at)
    except OrchestratorError:
        assignments = {}
    BoardApp(store, project_dir.name, assignments=assignments).run()
    return 0


def handle_board(args: argparse.Namespace) -> int:
    project_dir = resolve_project_dir(args)
    if not is_interactive():
        raise FactoryError("factory board requires an interactive terminal.")
    return open_board(project_dir)


def handle_usage(args: argparse.Namespace) -> int:
    command = getattr(args, "usage_command", None)
    if not command:
        raise FactoryError("Choose a usage command: record or list.")
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        raise FactoryError(f"Project directory does not exist: {project_dir}")
    if command == "record":
        return metrics.record_usage(
            project_dir,
            scope=args.scope,
            ref=args.ref,
            tool_id=args.tool_id,
            input_tokens=args.input_tokens,
            output_tokens=args.output_tokens,
            cost_usd=args.cost_usd,
            note=args.note,
        )
    if command == "import":
        return metrics.import_usage(project_dir, args.path)
    if command == "capture":
        return metrics.capture_usage(
            project_dir,
            args.tool_id,
            args.ref,
            scope=args.scope,
            source=args.source,
            note=args.note,
        )
    print(metrics.render_usage_text(project_dir, args.by))
    return 0


def handle_budget(args: argparse.Namespace) -> int:
    command = getattr(args, "budget_command", None)
    if not command:
        raise FactoryError("Choose a budget command: set, list, or remove.")
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        raise FactoryError(f"Project directory does not exist: {project_dir}")
    if command == "set":
        return metrics.set_budget(project_dir, args.key, args.limit)
    if command == "remove":
        return metrics.remove_budget(project_dir, args.key)
    return metrics.list_budgets(project_dir)


def open_dashboard(project_dir: Path) -> int:
    DashboardApp(
        lambda granularity: metrics.build_dashboard(project_dir, granularity),
        project_dir.name,
    ).run()
    return 0


def handle_dashboard(args: argparse.Namespace) -> int:
    project_dir = resolve_project_dir(args)
    if not is_interactive():
        print(metrics.render_dashboard_text(project_dir))
        return 0
    return open_dashboard(project_dir)


def handle_stack_configuration(args: argparse.Namespace) -> int:
    if not args.stack_command:
        raise FactoryError("Choose a stack command: plan, apply, or validate.")
    project_dir = Path(args.project_dir).resolve()
    if not project_dir.is_dir():
        raise FactoryError(f"Project directory does not exist: {project_dir}")
    if args.stack_command == "validate":
        errors, warnings = configuration_problems(project_dir, require_state=True)
        if errors:
            print("Stack configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
        else:
            print(f"Stack configuration validation passed: {project_dir}")
        if warnings:
            print("Warnings:")
            for warning in warnings:
                print(f"  - {warning}")
        return 1 if errors else 0

    plan = create_configuration_plan(project_dir)
    print(plan.render())
    if args.stack_command == "plan":
        return 0 if plan.ready else 1
    if not plan.ready:
        return 1

    resolutions = None
    if is_interactive():
        review_plan = ScaffoldPublishPlan(
            project_dir=plan.project_dir,
            source_sha256=plan.source_sha256,
            adapters=[],
            actions=[
                ScaffoldAction(
                    path=action.path,
                    status=action.status,
                    reason=action.reason,
                    output=(
                        ScaffoldOutput(
                            path=action.output.path,
                            content=action.output.content,
                            adapter_id=action.output.configurator_id,
                        )
                        if action.output is not None
                        else None
                    ),
                    existing_sha256=action.existing_sha256,
                )
                for action in plan.actions
            ],
        )
        reviewed = ScaffoldReviewApp(
            review_plan,
            render_stack_configuration_review(plan),
            noun="configuration",
        ).run()
        if reviewed is None:
            print("Stack configuration cancelled; no project files were changed.")
            return 0
        resolutions = {
            path: ConfigurationOutput(
                path=output.path,
                content=output.content,
                configurator_id=output.adapter_id,
            )
            for path, output in reviewed.items()
        }
    unresolved = apply_configuration_plan(plan, resolutions)
    if unresolved:
        print("Applied safe stack configuration; existing files were preserved.")
        print("Resolve configuration proposals:")
        for path in unresolved:
            print(f"  - {path}")
        return 1
    print(f"Stack configuration applied: {project_dir}")
    return 0


def render_stack_configuration_review(plan: ConfigurationPlan) -> str:
    lines = [
        "# Stack configuration review",
        "",
        "Factory derived these deterministic files from Approved stack decisions.",
        "Existing files are never replaced without explicit conflict review.",
        "",
        "## Configurators",
        "",
    ]
    lines.extend(f"- `{item}`" for item in plan.configurators)
    lines.extend(("", "## Files", ""))
    lines.extend(
        f"- **{action.status}** `{action.path}` — {action.reason}"
        for action in plan.actions
    )
    if plan.warnings:
        lines.extend(("", "## Boundaries", ""))
        lines.extend(f"- {warning}" for warning in plan.warnings)
    return "\n".join(lines) + "\n"


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


def handle_clarify(args: argparse.Namespace) -> int:
    project_dir = Path(args.project_dir).resolve()
    if not is_interactive():
        raise FactoryError("factory clarify requires an interactive terminal.")
    path = resolve_clarification(project_dir, args.identifier)
    try:
        clarification = load_clarification(path)
    except (OSError, ValueError) as exc:
        raise FactoryError(str(exc)) from exc
    clarification_app = ClarificationApp(clarification)
    result = clarification_app.run()
    if result == "review":
        answers = clarification_app.pending_answers or {}
        review = render_clarification_review(clarification, answers)
        if ReviewApp(review, accept_label="Submit answers").run():
            save_clarification(clarification, answers, submit=True)
            print(f"Clarification submitted: {path}")
        else:
            print("Clarification submission cancelled; no answers were changed.")
    elif result == "saved":
        print(f"Clarification progress saved: {path}")
    else:
        print("Clarification cancelled; no answers were changed.")
    return 0


def render_init_review(
    bundle: dict,
    intake: ProjectIntake,
    specs_markdown: str,
    deterministic_markdown: str,
    link_mode: str,
) -> str:
    files = "\n".join(f"- `{path}`" for path in sorted(bundle))
    diff = render_diff(
        deterministic_markdown,
        specs_markdown,
        "deterministic/project-specs.md",
        "refined/project-specs.md",
    )
    return (
        "# Project initialization review\n\n"
        f"- Factory link: {link_mode}\n"
        f"- AI tool kit: {intake.tool_kit_level}\n"
        "- No application source or dependencies will be generated.\n\n"
        f"{render_confidence_review(intake, heading_level=2)}\n"
        f"## Generated files\n\n{files}\n\n"
        f"## Refinement diff\n\n{diff}\n\n"
        f"## Project specs\n\n{specs_markdown}"
    )


def refine_with_feedback(
    intake: ProjectIntake,
    timeout: int,
    interactive: bool,
) -> Optional[Tuple[str, Optional[str]]]:
    if interactive and intake.use_ai and intake.refiner:
        return RefinementApp(
            intake.refiner,
            lambda progress, cancel_event: refine_specs(
                intake,
                timeout=timeout,
                progress=progress,
                cancel_event=cancel_event,
            ),
        ).run()

    progress = None
    if intake.use_ai and intake.refiner:
        print(f"Refining project specs with {intake.refiner}…", file=sys.stderr)

        def report(message: str) -> None:
            print(f"  {message}", file=sys.stderr)

        progress = report
    return refine_specs(intake, timeout=timeout, progress=progress)


def configure_refinement_after_draft(
    intake: ProjectIntake,
    tool_availability: dict,
    allow_ai: bool = True,
) -> bool:
    """Review the deterministic draft before choosing optional AI refinement."""
    while True:
        draft = render_project_specs(intake)
        review = (
            "# Draft review\n\n"
            + render_confidence_review(intake, heading_level=2)
            + "\n## Project specs\n\n"
            + draft
        )
        decision = DraftReviewApp(
            review,
            can_refine=allow_ai and bool(intake.tools),
        ).run()
        if decision is None:
            return False
        if decision == "publish":
            intake.use_ai = False
            return True

        settings = RefinementConfigApp(
            enabled_tools=list(intake.tools),
            default_refiner=intake.refiner,
            sections=list(intake.refinement_sections),
            timeout_seconds=intake.refinement_timeout_seconds,
            tool_availability=tool_availability,
        ).run()
        if settings is None:
            continue
        intake.refiner = settings.tool_id
        intake.use_ai = True
        intake.refinement_sections = list(settings.sections)
        intake.refinement_timeout_seconds = settings.timeout_seconds
        intake.validate()
        return True


def review_refined_sections(
    intake: ProjectIntake,
    refined_markdown: str,
    interactive: bool,
) -> str:
    """Apply only owner-selected, in-scope AI section changes."""
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
    elif interactive:
        review = SectionReviewApp(
            deterministic,
            refined_markdown,
            target_headings or None,
        )
        selected_markdown = review.run() or deterministic
        accepted = list(review.accepted_sections)
        rejected = list(review.rejected_sections)
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


def render_import_review(plan, project_dir: Path) -> str:
    sections = ["# Import review", "", "```text", plan.render(), "```"]
    for action in plan.conflicts:
        path = project_dir / action.path
        if not path.is_file():
            continue
        if action.proposed_content is None:
            sections.extend(
                (
                    "",
                    f"## Deactivation: `{action.path}`",
                    "",
                    "This previously generated file is no longer active in the proposed "
                    "policy. Removal requires an explicit choice in the Existing files tab.",
                )
            )
            continue
        sections.extend(
            (
                "",
                f"## Conflict: `{action.path}`",
                "",
                render_diff(
                    path.read_text(encoding="utf-8"),
                    action.proposed_content,
                    f"existing/{action.path}",
                    f"proposed/{action.path}",
                ),
            )
        )
    return "\n".join(sections)


def render_tooling_review(project_dir: Path, policy_yaml: str, plan) -> str:
    policy_path = project_dir / TOOL_POLICY_PATH
    current_policy = (
        policy_path.read_text(encoding="utf-8") if policy_path.is_file() else ""
    )
    sections = [
        "# AI tool kit review",
        "",
        "Provider files are project-local. Factory does not change global settings, "
        "credentials, model selection, telemetry, or provider endpoints.",
        "",
        "## Canonical policy",
        "",
        render_diff(
            current_policy,
            policy_yaml,
            f"current/{TOOL_POLICY_PATH}",
            f"proposed/{TOOL_POLICY_PATH}",
        ),
        "",
        "## File plan",
        "",
        "```text",
        plan.render().replace("Import plan:", "Tooling plan:", 1),
        "```",
    ]
    for action in plan.conflicts:
        path = project_dir / action.path
        if not path.is_file() or action.proposed_content is None:
            continue
        sections.extend(
            (
                "",
                f"## Conflict: `{action.path}`",
                "",
                render_diff(
                    path.read_text(encoding="utf-8"),
                    action.proposed_content,
                    f"existing/{action.path}",
                    f"proposed/{action.path}",
                ),
            )
        )
    return "\n".join(sections)


def render_scaffold_review(plan) -> str:
    project_dir = Path(plan.project_dir)
    sections = [
        "# Source scaffold review",
        "",
        "Generators ran only in an isolated staging directory. No dependencies "
        "were installed globally and no project source has been changed yet.",
        "",
        "## Publish plan",
        "",
        "```text",
        plan.render(),
        "```",
    ]
    for action in plan.conflicts:
        output = action.output
        existing = project_dir / action.path
        if output is None or not existing.is_file():
            continue
        sections.extend(("", f"## Conflict: `{action.path}`", ""))
        proposed_text = output.text
        try:
            existing_text = existing.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            existing_text = None
        if proposed_text is None or existing_text is None:
            sections.append(
                f"Binary conflict. Proposed size: {len(output.content)} bytes; "
                f"sha256: `{sha256(output.content).hexdigest()}`."
            )
        else:
            sections.append(
                render_diff(
                    existing_text,
                    proposed_text,
                    f"existing/{action.path}",
                    f"scaffold/{action.path}",
                )
            )
    return "\n".join(sections)


def render_diff(before: str, after: str, before_name: str, after_name: str) -> str:
    if before == after:
        return "_No content changes._"
    lines = difflib.unified_diff(
        before.splitlines(),
        after.splitlines(),
        fromfile=before_name,
        tofile=after_name,
        lineterm="",
    )
    return "```diff\n" + "\n".join(lines) + "\n```"


def render_clarification_review(clarification, answers: dict) -> str:
    lines = ["# Clarification review", ""]
    for question in clarification.questions:
        if not clarification.is_active(question, answers):
            continue
        answer = answers.get(question.question_id)
        if isinstance(answer, list):
            rendered = ", ".join(str(item) for item in answer)
        else:
            rendered = str(answer)
        lines.extend((f"## {question.prompt}", "", rendered or "_No answer_", ""))
    return "\n".join(lines)


def handle_shell(args: argparse.Namespace, parser: argparse.ArgumentParser) -> int:
    """Launch the interactive REPL (or print help outside a TTY)."""
    if not is_interactive():
        parser.print_help()
        return 0

    from .shell import run_shell

    preselected: Optional[Path] = None
    if getattr(args, "project", None):
        preselected = registry.resolve_project(args.project).resolve()
    elif getattr(args, "project_dir", None):
        preselected = Path(args.project_dir).resolve()
    return run_shell(preselected=preselected)


def is_interactive() -> bool:
    return bool(sys.stdin.isatty() and sys.stdout.isatty())


if __name__ == "__main__":
    raise SystemExit(main())
