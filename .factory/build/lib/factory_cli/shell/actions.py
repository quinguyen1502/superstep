"""Registry of factory actions exposed by the interactive shell.

Every ``factory`` subcommand has a matching :class:`Action`. Phase 1 uses this
registry only for discovery (palette, quick buttons, suggestions) — actual
dispatch still goes through the argv-based command routing in ``main.py``.
Later phases will add per-action argument forms and inline execution built on
the same records.

Keeping the registry static (instead of introspecting argparse) makes the
mapping between the CLI and the shell explicit, so a new subcommand is
consciously exposed to the hub rather than silently omitted or double-listed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, List, Tuple


class ActionKind(str, Enum):
    """How the shell should execute the action.

    - ``TUI``: opens a Textual sub-app (board, dashboard, wizards).
    - ``READ``: runs a read-only CLI subcommand and shows the output.
    - ``MUTATING``: changes on-disk state; the shell must confirm first.
    """

    TUI = "tui"
    READ = "read"
    MUTATING = "mutating"


class ActionMode(str, Enum):
    """Whether an action is available before / after a project is selected."""

    GLOBAL = "global"
    PROJECT = "project"
    BOTH = "both"


@dataclass(frozen=True)
class Action:
    """A single factory operation exposed to the shell."""

    id: str
    label: str
    description: str
    category: str
    kind: ActionKind
    mode: ActionMode
    argv: Tuple[str, ...]
    aliases: Tuple[str, ...] = field(default_factory=tuple)

    @property
    def requires_project(self) -> bool:
        return self.mode == ActionMode.PROJECT


def _act(
    id: str,
    label: str,
    description: str,
    category: str,
    kind: ActionKind,
    mode: ActionMode,
    argv: Iterable[str],
    aliases: Iterable[str] = (),
) -> Action:
    return Action(
        id=id,
        label=label,
        description=description,
        category=category,
        kind=kind,
        mode=mode,
        argv=tuple(argv),
        aliases=tuple(aliases),
    )


# Order matters for the palette: within the same category, more common actions
# come first so a fuzzy match on a short prefix still returns the useful entry.
ACTIONS: Tuple[Action, ...] = (
    # Global project management --------------------------------------------------
    _act(
        "init",
        "Init new project",
        "Create a new factory project (opens the interactive wizard).",
        "Project",
        ActionKind.MUTATING,
        ActionMode.GLOBAL,
        ("init",),
        aliases=("new", "create"),
    ),
    _act(
        "import",
        "Import existing repo",
        "Import factory assets into an existing project directory.",
        "Project",
        ActionKind.MUTATING,
        ActionMode.GLOBAL,
        ("import",),
    ),
    _act(
        "projects.list",
        "List registered projects",
        "Show every project in the global factory registry.",
        "Project",
        ActionKind.READ,
        ActionMode.GLOBAL,
        ("projects", "list"),
    ),
    _act(
        "projects.add",
        "Register a project",
        "Add an existing factory project to the registry.",
        "Project",
        ActionKind.MUTATING,
        ActionMode.GLOBAL,
        ("projects", "add"),
    ),
    _act(
        "projects.remove",
        "Unregister a project",
        "Remove a project from the registry (files are untouched).",
        "Project",
        ActionKind.MUTATING,
        ActionMode.GLOBAL,
        ("projects", "remove"),
    ),
    _act(
        "validate",
        "Validate project",
        "Check the expected structure, storage backend, and usage metrics.",
        "Project",
        ActionKind.READ,
        ActionMode.BOTH,
        ("validate",),
    ),
    _act(
        "ready",
        "Ready for implementation",
        "Check discovery, requirements, and todo tasks before implementation work.",
        "Project",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("ready",),
    ),
    # Specifications & clarifications --------------------------------------------
    _act(
        "specs",
        "Edit specifications",
        "Open the specification editor for the current project.",
        "Specs",
        ActionKind.TUI,
        ActionMode.PROJECT,
        ("specs",),
        aliases=("spec",),
    ),
    _act(
        "clarify",
        "Answer a clarification",
        "Open a CLAR-xxxx artifact and record answers interactively.",
        "Specs",
        ActionKind.TUI,
        ActionMode.PROJECT,
        ("clarify",),
    ),
    # Tool kits ------------------------------------------------------------------
    _act(
        "tools.status",
        "Tool kit status",
        "Show the active tool policy and drift status.",
        "Tools",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("tools", "status"),
    ),
    _act(
        "tools.configure",
        "Configure tool kit",
        "Open the tool-kit configurator to review policy and generated files.",
        "Tools",
        ActionKind.TUI,
        ActionMode.PROJECT,
        ("tools", "configure"),
    ),
    _act(
        "tools.plan",
        "Preview tool changes",
        "Preview provider files derived from the canonical policy.",
        "Tools",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("tools", "plan"),
    ),
    _act(
        "tools.apply",
        "Apply tool policy",
        "Publish reviewed provider files without overwriting conflicts.",
        "Tools",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("tools", "apply"),
    ),
    _act(
        "tools.validate",
        "Validate tool policy",
        "Validate policy, generated assets, and drift.",
        "Tools",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("tools", "validate"),
    ),
    # Skills ---------------------------------------------------------------------
    _act(
        "skills.plan",
        "Preview skill changes",
        "Preview skill files derived from framework templates for enabled tools.",
        "Skills",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("skills", "plan"),
    ),
    _act(
        "skills.apply",
        "Apply skill templates",
        "Emit framework skill files for enabled tools without overwriting conflicts.",
        "Skills",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("skills", "apply"),
    ),
    _act(
        "skills.validate",
        "Validate skill drift",
        "Check that emitted skill files match framework templates.",
        "Skills",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("skills", "validate"),
    ),
    # Scaffolding ----------------------------------------------------------------
    _act(
        "scaffold.plan",
        "Preview scaffold plan",
        "Preview scaffold adapters, commands, and expected source paths.",
        "Scaffold",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("scaffold", "plan"),
    ),
    _act(
        "scaffold.apply",
        "Apply scaffold",
        "Run approved adapters in staging and publish reviewed output.",
        "Scaffold",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("scaffold", "apply"),
    ),
    _act(
        "scaffold.validate",
        "Validate scaffold",
        "Validate managed scaffold output and source decisions.",
        "Scaffold",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("scaffold", "validate"),
    ),
    # Dependencies ---------------------------------------------------------------
    _act(
        "deps.plan",
        "Preview dependency plan",
        "Preview dependency managers, commands, and network access.",
        "Dependencies",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("deps", "plan"),
    ),
    _act(
        "deps.apply",
        "Install dependencies",
        "Run reviewed project-local dependency installation.",
        "Dependencies",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("deps", "apply"),
    ),
    _act(
        "deps.validate",
        "Validate dependencies",
        "Validate dependency provenance and local environments.",
        "Dependencies",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("deps", "validate"),
    ),
    # Verification ---------------------------------------------------------------
    _act(
        "verify.plan",
        "Preview verification",
        "Preview deterministic project validation checks.",
        "Verify",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("verify", "plan"),
    ),
    _act(
        "verify.run",
        "Run verification",
        "Run reviewed checks and record verification evidence.",
        "Verify",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("verify", "run"),
    ),
    _act(
        "verify.validate",
        "Validate verification",
        "Validate the latest verification evidence.",
        "Verify",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("verify", "validate"),
    ),
    # Stack configuration --------------------------------------------------------
    _act(
        "stack.plan",
        "Preview stack config",
        "Preview configuration derived from Approved stack choices.",
        "Stack",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("stack", "plan"),
    ),
    _act(
        "stack.apply",
        "Apply stack config",
        "Publish reviewed stack configuration without overwriting conflicts.",
        "Stack",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("stack", "apply"),
    ),
    _act(
        "stack.validate",
        "Validate stack config",
        "Validate managed stack configuration and decision drift.",
        "Stack",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("stack", "validate"),
    ),
    # Orchestration --------------------------------------------------------------
    _act(
        "orchestrate.plan",
        "Preview orchestration",
        "Preview task-to-tool assignments and worktree layout.",
        "Orchestrate",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("orchestrate", "plan"),
        aliases=("dispatch plan",),
    ),
    _act(
        "orchestrate.run",
        "Run orchestration",
        "Create worktrees, write briefs, and move todo tasks to doing.",
        "Orchestrate",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("orchestrate", "run"),
        aliases=("dispatch",),
    ),
    _act(
        "orchestrate.status",
        "Orchestration status",
        "Show recorded orchestration worktrees and tools.",
        "Orchestrate",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("orchestrate", "status"),
    ),
    _act(
        "orchestrate.validate",
        "Validate orchestration",
        "Validate orchestration state against live worktrees.",
        "Orchestrate",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("orchestrate", "validate"),
    ),
    _act(
        "orchestrate.cleanup",
        "Cleanup orchestration",
        "Remove clean factory-created worktrees and prune state.",
        "Orchestrate",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("orchestrate", "cleanup"),
    ),
    # Tasks & board --------------------------------------------------------------
    _act(
        "board",
        "Kanban board",
        "Open the interactive Kanban board with staged moves.",
        "Tasks",
        ActionKind.TUI,
        ActionMode.PROJECT,
        ("board",),
        aliases=("kanban", "tasks"),
    ),
    _act(
        "task.create",
        "Create task",
        "Create a new lifecycle task artifact.",
        "Tasks",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("task", "create"),
    ),
    _act(
        "task.move",
        "Move task",
        "Move a task artifact to another lifecycle column.",
        "Tasks",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("task", "move"),
    ),
    _act(
        "task.archive",
        "Archive tasks",
        "Move finished tasks out of the board into the archive folder.",
        "Tasks",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("task", "archive"),
    ),
    _act(
        "gc",
        "Preview factory-state gc",
        "Show which done tasks and companion artifacts would move to the archive.",
        "Tasks",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("gc",),
        aliases=("compact",),
    ),
    _act(
        "gc.apply",
        "Apply factory-state gc",
        "Archive old done tasks and companion REV/QA/SUM artifacts.",
        "Tasks",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("gc", "--apply"),
    ),
    _act(
        "ids.check",
        "Check artifact IDs",
        "Fail when any TYPE-NNNN artifact ID names more than one artifact.",
        "Tasks",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("ids", "check"),
    ),
    _act(
        "ids.next",
        "Next artifact ID",
        "Print the next free artifact ID per type (TASK, REV, QA, ...).",
        "Tasks",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("ids", "next"),
    ),
    # Metrics & budgets ----------------------------------------------------------
    _act(
        "dashboard",
        "Metrics dashboard",
        "Open the token/cost dashboard with KPI cards and charts.",
        "Metrics",
        ActionKind.TUI,
        ActionMode.PROJECT,
        ("dashboard",),
        aliases=("metrics",),
    ),
    _act(
        "usage.record",
        "Record usage",
        "Record a single token/cost usage entry.",
        "Metrics",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("usage", "record"),
    ),
    _act(
        "usage.capture",
        "Capture usage from tool",
        "Parse a coding tool's JSON output and record one usage entry.",
        "Metrics",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("usage", "capture"),
    ),
    _act(
        "usage.import",
        "Import usage file",
        "Bulk-import usage records from a JSONL or CSV file.",
        "Metrics",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("usage", "import"),
    ),
    _act(
        "usage.list",
        "List usage",
        "Summarize recorded token/cost usage by ref, tool, scope, or budget.",
        "Metrics",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("usage", "list"),
    ),
    _act(
        "budget.list",
        "List budgets",
        "List token budgets and current usage.",
        "Metrics",
        ActionKind.READ,
        ActionMode.PROJECT,
        ("budget", "list"),
    ),
    _act(
        "budget.set",
        "Set a budget",
        "Set a token budget for a task or agent key.",
        "Metrics",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("budget", "set"),
    ),
    _act(
        "budget.remove",
        "Remove a budget",
        "Remove a token budget by key.",
        "Metrics",
        ActionKind.MUTATING,
        ActionMode.PROJECT,
        ("budget", "remove"),
    ),
)


def actions_for_mode(mode: ActionMode) -> List[Action]:
    """Return actions visible in the given shell mode.

    ``ActionMode.GLOBAL`` includes ``BOTH`` actions; likewise for ``PROJECT``.
    """
    if mode is ActionMode.GLOBAL:
        return [a for a in ACTIONS if a.mode in (ActionMode.GLOBAL, ActionMode.BOTH)]
    if mode is ActionMode.PROJECT:
        return [a for a in ACTIONS if a.mode in (ActionMode.PROJECT, ActionMode.BOTH)]
    return list(ACTIONS)
