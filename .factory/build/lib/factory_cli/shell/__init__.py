"""Interactive Factory shell.

REPL-based launcher backed by prompt_toolkit for input (fuzzy completion,
history, editing) and rich for output. It exposes every ``factory``
subcommand through a stable :class:`Action` registry and per-action
:class:`FormField` specs, so users never have to memorize command names or
flags.

The shell reuses the existing CLI as a subprocess for read-only commands
and hands the parent terminal over for interactive commands (board,
dashboard, wizards). It never re-implements business logic.
"""

from .actions import ACTIONS, Action, ActionKind, ActionMode, actions_for_mode
from .context import ProjectOverview, ShellContext
from .forms import FORM_SPECS, FieldKind, FormField, build_argv, form_for, validate_values
from .repl import FactoryRepl, resolve_action, run_shell
from .runner import CommandResult, run_factory

__all__ = [
    "ACTIONS",
    "Action",
    "ActionKind",
    "ActionMode",
    "actions_for_mode",
    "ProjectOverview",
    "ShellContext",
    "FORM_SPECS",
    "FieldKind",
    "FormField",
    "build_argv",
    "form_for",
    "validate_values",
    "FactoryRepl",
    "resolve_action",
    "run_shell",
    "CommandResult",
    "run_factory",
]
