"""Per-action argument form specs.

Hand-written on purpose: introspecting argparse would leak internal details
(dest names, private groups) and silently pick up new subcommand arguments
that need explicit UX review before appearing in the hub. Keeping the map
here forces someone adding a new mutating command to think about the form.

Only forms for *simple* mutating actions live here. Complex mutating actions
that already own an interactive review flow (``scaffold apply``, ``deps
apply``, ``tools configure``, ``orchestrate run``, …) are handled by the
generic confirm modal in :mod:`.app` and dispatched via the normal CLI.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Iterable, List, Optional, Tuple

from ..constants import (
    PROJECT_PRESET_IDS,
    TASK_STATES,
    TOOL_IDS,
    TOOL_KIT_LEVELS,
    USAGE_SCOPES,
)


class FieldKind(str, Enum):
    TEXT = "text"
    INT = "int"
    PATH = "path"
    CHOICE = "choice"


@dataclass(frozen=True)
class FormField:
    """A single input on an action's argument form.

    ``argv`` names the CLI flag emitted for this field. An empty string means
    the value is passed positionally, in the order the fields are declared.
    ``required`` inputs must be non-empty at submit; ``INT`` fields also fail
    validation if the value does not parse.
    """

    key: str
    label: str
    kind: FieldKind
    argv: str = ""
    required: bool = False
    default: str = ""
    choices: Tuple[str, ...] = ()
    help: str = ""


def _f(
    key: str,
    label: str,
    kind: FieldKind,
    argv: str = "",
    required: bool = False,
    default: str = "",
    choices: Iterable[str] = (),
    help: str = "",
) -> FormField:
    return FormField(
        key=key,
        label=label,
        kind=kind,
        argv=argv,
        required=required,
        default=default,
        choices=tuple(choices),
        help=help,
    )


FORM_SPECS: Dict[str, Tuple[FormField, ...]] = {
    "init": (
        _f(
            "project_name",
            "Project name",
            FieldKind.TEXT,
            required=True,
            help="Folder to create next to the current directory.",
        ),
        _f(
            "directory",
            "Parent directory",
            FieldKind.PATH,
            argv="-C",
            default=".",
            help="Where to create the project folder (default: current directory).",
        ),
        _f(
            "tool_kit",
            "Tool kit",
            FieldKind.CHOICE,
            argv="--tool-kit",
            default="instructions",
            choices=TOOL_KIT_LEVELS,
        ),
        _f(
            "preset",
            "Preset (optional)",
            FieldKind.CHOICE,
            argv="--preset",
            choices=PROJECT_PRESET_IDS,
            help="Fill blank stack fields as Proposed.",
        ),
        _f(
            "intake_path",
            "Intake YAML (optional)",
            FieldKind.PATH,
            argv="--intake",
        ),
        _f(
            "specs_path",
            "Project specs markdown (optional)",
            FieldKind.PATH,
            argv="--from-specs",
        ),
    ),
    "import": (
        _f(
            "project_dir",
            "Project directory",
            FieldKind.PATH,
            required=True,
            default=".",
        ),
        _f(
            "tool_kit",
            "Tool kit",
            FieldKind.CHOICE,
            argv="--tool-kit",
            default="instructions",
            choices=TOOL_KIT_LEVELS,
        ),
    ),
    "usage.capture": (
        _f(
            "tool",
            "Tool",
            FieldKind.CHOICE,
            argv="--tool",
            required=True,
            choices=TOOL_IDS,
        ),
        _f("ref", "Reference", FieldKind.TEXT, argv="--ref", required=True),
        _f(
            "scope",
            "Scope",
            FieldKind.CHOICE,
            argv="--scope",
            default="task",
            choices=USAGE_SCOPES,
        ),
        _f(
            "source",
            "Source file",
            FieldKind.PATH,
            argv="--from",
            required=True,
            help="JSON/JSONL output from the tool. Pipe via CLI if you need stdin.",
        ),
        _f("note", "Note (optional)", FieldKind.TEXT, argv="--note"),
    ),
    "task.create": (
        _f("task_id", "Task ID", FieldKind.TEXT, required=True, help="e.g. TASK-0042"),
        _f("title", "Title", FieldKind.TEXT, required=True),
        _f(
            "state",
            "Initial column",
            FieldKind.CHOICE,
            argv="--state",
            default="backlog",
            choices=TASK_STATES,
        ),
    ),
    "ids.check": (
        _f(
            "ref",
            "Git ref (optional)",
            FieldKind.TEXT,
            argv="--ref",
            help="Also scan a fetched ref, e.g. origin/develop.",
        ),
    ),
    "ids.next": (
        _f(
            "type",
            "Artifact type (optional)",
            FieldKind.TEXT,
            help="e.g. TASK, REV, QA; empty lists every type in use.",
        ),
        _f(
            "ref",
            "Git ref (optional)",
            FieldKind.TEXT,
            argv="--ref",
            help="Also scan a fetched ref, e.g. origin/develop.",
        ),
    ),
    "task.move": (
        _f("task_id", "Task ID", FieldKind.TEXT, required=True),
        _f(
            "state",
            "Target column",
            FieldKind.CHOICE,
            required=True,
            choices=TASK_STATES,
        ),
    ),
    "task.archive": (
        _f("task_id", "Task ID prefix (optional)", FieldKind.TEXT),
        _f(
            "state",
            "State to archive from",
            FieldKind.CHOICE,
            argv="--state",
            default="done",
            choices=TASK_STATES,
        ),
    ),
    "projects.add": (
        _f("path", "Project path", FieldKind.PATH, required=True, default="."),
        _f("name", "Registry name (optional)", FieldKind.TEXT, argv="--name"),
    ),
    "projects.remove": (
        _f("name", "Registered name", FieldKind.TEXT, required=True),
    ),
    "budget.set": (
        _f(
            "key",
            "Budget key",
            FieldKind.TEXT,
            required=True,
            help="task:TASK-0001 or agent:developer",
        ),
        _f("limit", "Token limit", FieldKind.INT, required=True),
    ),
    "budget.remove": (
        _f("key", "Budget key", FieldKind.TEXT, required=True),
    ),
    "usage.record": (
        _f(
            "scope",
            "Scope",
            FieldKind.CHOICE,
            argv="--scope",
            required=True,
            default="task",
            choices=USAGE_SCOPES,
        ),
        _f("ref", "Reference", FieldKind.TEXT, argv="--ref", required=True),
        _f(
            "tool",
            "Tool",
            FieldKind.CHOICE,
            argv="--tool",
            choices=TOOL_IDS,
        ),
        _f("input_tokens", "Input tokens", FieldKind.INT, argv="--in"),
        _f("output_tokens", "Output tokens", FieldKind.INT, argv="--out"),
        _f("cost_usd", "Cost (USD)", FieldKind.TEXT, argv="--cost"),
        _f("note", "Note (optional)", FieldKind.TEXT, argv="--note"),
    ),
    "usage.import": (
        _f(
            "path",
            "Source file",
            FieldKind.PATH,
            required=True,
            help=".jsonl or .csv",
        ),
    ),
    "clarify": (
        _f(
            "identifier",
            "Clarification ID or artifact path",
            FieldKind.TEXT,
            required=True,
        ),
    ),
}


def form_for(action_id: str) -> Optional[Tuple[FormField, ...]]:
    return FORM_SPECS.get(action_id)


def validate_values(
    spec: Iterable[FormField], values: Dict[str, str]
) -> List[str]:
    """Return a list of human-readable validation errors ("" on success)."""
    errors: List[str] = []
    for field in spec:
        raw = values.get(field.key, "").strip()
        if not raw:
            if field.required:
                errors.append(f"{field.label} is required.")
            continue
        if field.kind is FieldKind.INT:
            try:
                int(raw)
            except ValueError:
                errors.append(f"{field.label} must be an integer.")
        elif field.kind is FieldKind.CHOICE and field.choices and raw not in field.choices:
            errors.append(
                f"{field.label} must be one of: {', '.join(field.choices)}."
            )
    return errors


def build_argv(
    base_argv: Iterable[str],
    spec: Iterable[FormField],
    values: Dict[str, str],
    project_path: Optional[str] = None,
) -> List[str]:
    """Assemble the CLI argv from base tokens + form values."""
    argv: List[str] = list(base_argv)
    positionals: List[str] = []
    for field in spec:
        raw = values.get(field.key, "").strip()
        if not raw:
            continue
        if field.argv:
            argv.extend([field.argv, raw])
        else:
            positionals.append(raw)
    # Positionals come after the subcommand tokens, before any -C we add.
    argv.extend(positionals)
    if project_path and "-C" not in argv:
        argv.extend(["-C", project_path])
    return argv
