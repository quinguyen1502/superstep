"""prompt_toolkit + rich REPL that drives every factory subcommand.

Design goals:

- Match the mental model of ``claude``/``codex`` CLIs: a prompt loop with
  slash commands, fuzzy autocomplete, streaming output, and normal terminal
  scrollback. No full-screen takeover.
- Reuse the existing schema (``ACTIONS``, ``FORM_SPECS``) so a new
  subcommand becomes available in the shell as soon as it is added to the
  argparse tree.
- Never re-implement business logic: read-only actions are dispatched via
  ``python -m factory_cli`` in a captured subprocess; interactive actions
  (board, dashboard, wizards) hand the parent terminal over so their own
  Textual UIs render without nesting.

The REPL is a thin object with unit-testable pieces (``resolve_action``,
``FactoryRepl._collect_form``, ``FactoryRepl._run_argv``) so tests don't
need to drive a real terminal.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import yaml
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, FuzzyCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.validation import ValidationError, Validator
from rich.box import ROUNDED
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ..constants import TASK_STATES
from ..registry import ProjectEntry, factory_home, list_projects, resolve_project
from .actions import ACTIONS, Action, ActionKind, ActionMode, actions_for_mode
from .context import ProjectOverview, ShellContext
from .forms import FORM_SPECS, FieldKind, FormField, build_argv, form_for
from . import pipeline
from .runner import CommandResult, run_factory


# Actions whose handler opens its own Textual review flow: they must run in
# the parent's real terminal — a captured subprocess cannot render them.
_TERMINAL_ACTION_IDS = frozenset(
    {
        "init",
        "import",
        "specs",
        "clarify",
        "tools.configure",
        "tools.apply",
        "scaffold.apply",
        "deps.apply",
        "stack.apply",
        "orchestrate.run",
    }
)


_SLASH_COMMANDS: Tuple[Tuple[str, str], ...] = (
    ("/help",      "Show slash commands and keybinds."),
    ("/tour",      "Reshow the first-run onboarding text."),
    ("/pipeline",  "Show Factory milestones and where this project stands."),
    ("/status",    "Reprint the project overview."),
    ("/refresh",   "Refresh the overview from disk."),
    ("/project",   "Switch to a registered project. Usage: /project <name>."),
    ("/projects",  "List registered projects."),
    ("/quit",      "Leave the shell (or press Ctrl+D)."),
    ("/exit",      "Alias for /quit."),
)


def shell_state_path() -> Path:
    """Location of the shell's persistent state (tour flag, prefs)."""
    return factory_home() / "shell-state.yaml"


def load_shell_state() -> Dict[str, Any]:
    path = shell_state_path()
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}
    return data if isinstance(data, dict) else {}


def save_shell_state(state: Dict[str, Any]) -> None:
    path = shell_state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.write_text(
            yaml.safe_dump(state, sort_keys=False, allow_unicode=True),
            encoding="utf-8",
        )
    except OSError:
        # Persistence is best-effort — never crash the shell on a read-only
        # config directory or full disk.
        pass


_STATUS_STYLE: Dict[pipeline.StageStatus, Tuple[str, str]] = {
    pipeline.StageStatus.DONE:        ("●", "green"),
    pipeline.StageStatus.IN_PROGRESS: ("◐", "yellow"),
    pipeline.StageStatus.NOT_STARTED: ("○", "dim"),
}


_TOUR_STEPS: Tuple[Tuple[str, str], ...] = (
    (
        "Discover",
        "Type [cyan]/pipeline[/cyan] to see the Factory milestones and where "
        "this project stands. [cyan]/help[/cyan] lists slash commands; "
        "[cyan]Tab[/cyan] fuzzy-completes every subcommand.",
    ),
    (
        "Run",
        "Type an action name to run it — e.g. [cyan]board[/cyan], [cyan]dashboard[/cyan], "
        "[cyan]orchestrate.plan[/cyan]. Aliases (kanban, dispatch, new) resolve too.",
    ),
    (
        "Fill in",
        "Commands that need arguments (task.create, budget.set, usage.record) open "
        "a short form. Choice fields autocomplete; integer fields validate.",
    ),
    (
        "Confirm",
        "Every destructive command shows the exact [bold]factory ...[/bold] argv "
        "before running. Type [cyan]y[/cyan] to run, anything else to skip.",
    ),
    (
        "Leave",
        "[cyan]Ctrl+D[/cyan] or [cyan]/quit[/cyan] exits. History is saved to "
        "~/.factory/shell-history so [cyan]Ctrl+R[/cyan] can search past commands.",
    ),
)


def resolve_action(text: str) -> Optional[Action]:
    """Match ``text`` to an :class:`Action` by id, alias, or dotted prefix.

    Case-insensitive. Exact id wins; then any alias exact match; then a
    unique prefix on the id. Returns ``None`` if the match is ambiguous or
    missing.
    """
    query = text.strip().lower()
    if not query:
        return None
    exact = [a for a in ACTIONS if a.id.lower() == query]
    if len(exact) == 1:
        return exact[0]
    alias_hits = [a for a in ACTIONS if query in (alias.lower() for alias in a.aliases)]
    if len(alias_hits) == 1:
        return alias_hits[0]
    prefix_hits = [a for a in ACTIONS if a.id.lower().startswith(query)]
    if len(prefix_hits) == 1:
        return prefix_hits[0]
    return None


def _quote_argv(argv: Sequence[str]) -> str:
    return " ".join(shlex.quote(str(token)) for token in argv)


class _IntValidator(Validator):
    def validate(self, document) -> None:  # noqa: D401 - short prompt_toolkit hook
        text = document.text.strip()
        if not text:
            return
        try:
            int(text)
        except ValueError:
            raise ValidationError(message="Please enter an integer.")


class _ChoiceValidator(Validator):
    def __init__(self, choices: Sequence[str], required: bool) -> None:
        self.choices = tuple(choices)
        self.required = required

    def validate(self, document) -> None:
        text = document.text.strip()
        if not text:
            if self.required:
                raise ValidationError(message="Value required.")
            return
        if text not in self.choices:
            raise ValidationError(
                message=f"Choose one of: {', '.join(self.choices)}."
            )


class _RequiredValidator(Validator):
    def validate(self, document) -> None:
        if not document.text.strip():
            raise ValidationError(message="Value required.")


class FactoryCompleter(Completer):
    """Completes command names, slash commands, and known keywords."""

    def __init__(self) -> None:
        self._action_words: List[Tuple[str, str]] = []
        for action in ACTIONS:
            self._action_words.append((action.id, action.description))
            for alias in action.aliases:
                self._action_words.append((alias, action.description))
        self._slash_words = list(_SLASH_COMMANDS)

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        stripped = text.lstrip()
        if stripped.startswith("/"):
            for name, description in self._slash_words:
                if name.startswith(stripped):
                    yield Completion(
                        name,
                        start_position=-len(stripped),
                        display=name,
                        display_meta=description,
                    )
            return
        # Command / alias completion. Use full input as the query so nested
        # names like ``task.create`` complete after typing ``task``.
        query = stripped.lower()
        for word, description in self._action_words:
            if query in word.lower():
                yield Completion(
                    word,
                    start_position=-len(stripped),
                    display=word,
                    display_meta=description,
                )


@dataclass
class ReplConfig:
    """Ways tests inject fake terminal + subprocess behavior.

    ``prompt`` is any callable with the signature of
    :func:`prompt_toolkit.prompt`; ``runner`` is the READ-action runner; and
    ``terminal_runner`` executes the command with the terminal handed over.
    """

    prompt: Callable[..., str] = None  # type: ignore[assignment]
    runner: Callable[[Sequence[str]], CommandResult] = None  # type: ignore[assignment]
    terminal_runner: Callable[[Sequence[str]], int] = None  # type: ignore[assignment]


def _default_terminal_runner(argv: Sequence[str]) -> int:
    """Run the CLI without capturing so it can own the terminal."""
    process = subprocess.run(
        [sys.executable, "-m", "factory_cli", *argv],
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    return process.returncode


class FactoryRepl:
    """Interactive shell that drives the factory CLI."""

    def __init__(
        self,
        context: ShellContext,
        *,
        console: Optional[Console] = None,
        config: Optional[ReplConfig] = None,
    ) -> None:
        self.context = context
        self.console = console or Console()
        self._config = config or ReplConfig()
        history_path = factory_home() / "shell-history"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self._session: Optional[PromptSession] = PromptSession(
                history=FileHistory(str(history_path)),
                completer=FuzzyCompleter(FactoryCompleter()),
                complete_while_typing=True,
            )
        except Exception:  # noqa: BLE001 - fall back for exotic terminals
            self._session = None
        self._running = False

    # -- runners -------------------------------------------------------------

    def _run_captured(self, argv: Sequence[str]) -> CommandResult:
        if self._config.runner is not None:
            return self._config.runner(argv)
        return run_factory(list(argv))

    def _run_terminal(self, argv: Sequence[str]) -> int:
        if self._config.terminal_runner is not None:
            return self._config.terminal_runner(argv)
        return _default_terminal_runner(argv)

    def _prompt(self, message: str, **kwargs) -> str:
        if self._config.prompt is not None:
            return self._config.prompt(message, **kwargs)
        if self._session is None:
            return input(message)
        return self._session.prompt(message, **kwargs)

    # -- rendering -----------------------------------------------------------

    def _print_banner(self) -> None:
        project = (
            self.context.selected.name if self.context.selected else "(no project)"
        )
        title = Text.from_markup(f"[bold]Factory shell[/bold]  ·  {project}")
        hint = Text.from_markup(
            "Type an action name (e.g. [cyan]board[/cyan], [cyan]orchestrate.run[/cyan]), "
            "or [cyan]/help[/cyan] for slash commands. Ctrl+D to quit."
        )
        self.console.print(Panel.fit(title + Text("\n") + hint, box=ROUNDED))

    def _print_overview(self) -> None:
        overview = self.context.overview
        if overview is None:
            if not self.context.projects:
                self.console.print(
                    "[yellow]No projects registered.[/yellow]  Try [cyan]init[/cyan] or [cyan]projects.add[/cyan]."
                )
            else:
                self.console.print(
                    "[yellow]No project selected.[/yellow]  Use [cyan]/project <name>[/cyan] to pick one."
                )
            return
        table = Table(
            title=f"{overview.name}  (storage: {overview.storage_backend})",
            box=ROUNDED,
            show_header=True,
            header_style="bold",
        )
        for state in TASK_STATES:
            table.add_column(state.title(), justify="right")
        table.add_row(*(str(overview.task_counts.get(s, 0)) for s in TASK_STATES))
        self.console.print(table)
        extras: List[str] = []
        if overview.over_budget:
            extras.append(f"[red]over-budget keys: {overview.over_budget}[/red]")
        if overview.active_orchestrations:
            extras.append(
                f"active orchestrations: {overview.active_orchestrations}"
            )
        if overview.incomplete_areas:
            extras.append(
                f"[yellow]INCOMPLETE: {', '.join(overview.incomplete_areas)}[/yellow]"
            )
        if extras:
            self.console.print("  ·  ".join(extras))
        if overview.error:
            self.console.print(f"[red]warning: {overview.error}[/red]")

    def _print_pipeline(self) -> None:
        if self.context.selected is None:
            self.console.print(
                "[yellow]Pick a project first with[/yellow] "
                "[cyan]/project <name>[/cyan][yellow] to see its pipeline.[/yellow]"
            )
            return
        project_dir = Path(self.context.selected.path)
        evaluations = pipeline.evaluate(project_dir)
        table = Table(
            title=f"Factory pipeline — {self.context.selected.name}",
            box=ROUNDED,
            show_header=True,
            header_style="bold",
        )
        table.add_column("", width=3)
        table.add_column("Stage")
        table.add_column("What it does")
        table.add_column("Status")
        for evaluation in evaluations:
            glyph, style = _STATUS_STYLE[evaluation.status]
            label = evaluation.stage.label
            if evaluation.stage.optional:
                label += "  [dim](optional)[/dim]"
            table.add_row(
                f"[{style}]{glyph}[/{style}]",
                label,
                evaluation.stage.summary,
                f"[{style}]{evaluation.detail}[/{style}]",
            )
        self.console.print(table)
        suggested = pipeline.suggest_next(evaluations)
        if suggested is None:
            self.console.print(
                "[green]All milestones complete for this project.[/green]"
            )
        else:
            action = next(
                (a for a in ACTIONS if a.id == suggested.stage.next_action),
                None,
            )
            action_hint = action.label if action else suggested.stage.next_action
            self.console.print(
                f"[bold]Next:[/bold] {suggested.stage.label} — run "
                f"[cyan]{suggested.stage.next_action}[/cyan] ({action_hint}). "
                f"Docs: [dim]{suggested.stage.docs}[/dim]"
            )
        self.console.print(
            "\nLegend: [green]●[/green] done   [yellow]◐[/yellow] in progress   "
            "[dim]○[/dim] not started"
        )

    def _print_tour(self) -> None:
        lines = [Text.from_markup("[bold]Getting started[/bold]")]
        for index, (title, body) in enumerate(_TOUR_STEPS, start=1):
            lines.append(
                Text.from_markup(f"  [bold]{index}. {title}[/bold]  {body}")
            )
        lines.append(
            Text.from_markup(
                "\nRun [cyan]/tour[/cyan] any time to see this again, or "
                "[cyan]/help[/cyan] for the full slash-command list."
            )
        )
        body = Text("\n").join(lines)
        self.console.print(Panel(body, box=ROUNDED, border_style="cyan"))

    def _maybe_show_first_run_tour(self) -> None:
        state = load_shell_state()
        if state.get("tour_seen"):
            return
        self._print_tour()
        state["tour_seen"] = True
        save_shell_state(state)

    def _print_help(self) -> None:
        table = Table(title="Slash commands", box=ROUNDED, show_header=False)
        table.add_column("cmd", style="cyan")
        table.add_column("what")
        for name, description in _SLASH_COMMANDS:
            table.add_row(name, description)
        self.console.print(table)
        self.console.print(
            "\nType any action name (e.g. [cyan]board[/cyan], "
            "[cyan]dashboard[/cyan], [cyan]task.create[/cyan]) to run it. "
            "Tab completes across every factory subcommand and known alias."
        )

    def _print_projects(self) -> None:
        if not self.context.projects:
            self.console.print("No projects registered.")
            return
        table = Table(box=ROUNDED, show_header=True, header_style="bold")
        table.add_column("Name")
        table.add_column("Path")
        for entry in self.context.projects:
            marker = "→ " if self.context.selected and entry.name == self.context.selected.name else "  "
            table.add_row(f"{marker}{entry.name}", entry.path)
        self.console.print(table)

    # -- slash -------------------------------------------------------------

    def _handle_slash(self, line: str) -> None:
        parts = line[1:].split()
        if not parts:
            self._print_help()
            return
        cmd, args = parts[0].lower(), parts[1:]
        if cmd in ("q", "quit", "exit"):
            self._running = False
        elif cmd == "help":
            self._print_help()
        elif cmd == "tour":
            self._print_tour()
        elif cmd == "pipeline":
            self._print_pipeline()
        elif cmd == "status":
            self._print_overview()
        elif cmd == "refresh":
            self.context.refresh()
            self._print_overview()
        elif cmd == "projects":
            self._print_projects()
        elif cmd == "project":
            self._switch_project(args)
        else:
            self.console.print(f"[red]Unknown slash command:[/red] /{cmd}. Try /help.")

    def _switch_project(self, args: List[str]) -> None:
        if not args:
            self._print_projects()
            self.console.print("Usage: [cyan]/project <name>[/cyan]")
            return
        name = args[0]
        try:
            path = resolve_project(name)
        except Exception as exc:  # noqa: BLE001 - user typed a bad name
            self.console.print(f"[red]{exc}[/red]")
            return
        entry = next(
            (p for p in self.context.projects if Path(p.path).resolve() == path.resolve()),
            None,
        )
        if entry is None:
            entry = ProjectEntry(name=name, path=str(path), added_at="")
        self.context.select(entry)
        self.console.print(f"Switched to [bold]{entry.name}[/bold]  ({entry.path})")
        self._print_overview()

    # -- action dispatch ---------------------------------------------------

    def _collect_form(
        self, action: Action, spec: Tuple[FormField, ...]
    ) -> Optional[Dict[str, str]]:
        self.console.print(f"[bold]{action.label}[/bold] — {action.description}")
        values: Dict[str, str] = {}
        for field in spec:
            label = field.label
            if field.help:
                self.console.print(f"  [dim]{field.help}[/dim]")
            if field.kind is FieldKind.CHOICE and field.choices:
                validator = _ChoiceValidator(field.choices, field.required)
                completer = _wordlist_completer(field.choices)
                message = f"  {label} [{'/'.join(field.choices)}]: "
            elif field.kind is FieldKind.INT:
                validator = _IntValidator()
                completer = None
                message = f"  {label}: "
            elif field.required:
                validator = _RequiredValidator()
                completer = None
                message = f"  {label}: "
            else:
                validator = None
                completer = None
                message = f"  {label}: "
            try:
                raw = self._prompt(
                    message,
                    default=field.default,
                    validator=validator,
                    completer=completer,
                )
            except (KeyboardInterrupt, EOFError):
                self.console.print("[yellow]Cancelled.[/yellow]")
                return None
            values[field.key] = raw.strip()
        return values

    def _confirm(self, argv: Sequence[str]) -> bool:
        rendered = _quote_argv(argv)
        self.console.print(
            f"[yellow]About to run:[/yellow] [bold]factory[/bold] {rendered}"
        )
        try:
            answer = self._prompt("Confirm? [y/N]: ")
        except (KeyboardInterrupt, EOFError):
            return False
        return answer.strip().lower() in ("y", "yes")

    def _run_action(self, action: Action) -> None:
        spec = form_for(action.id)
        values: Dict[str, str] = {}
        if spec:
            collected = self._collect_form(action, spec)
            if collected is None:
                return
            values = collected
        project = (
            str(self.context.selected.path)
            if self.context.selected and action.requires_project
            else None
        )
        argv = build_argv(action.argv, spec or (), values, project_path=project)
        if action.kind is ActionKind.MUTATING and not self._confirm(argv):
            self.console.print("[yellow]Skipped.[/yellow]")
            return
        self._dispatch(action, argv)
        self.context.refresh()

    def _dispatch(self, action: Action, argv: Sequence[str]) -> None:
        if action.kind is ActionKind.TUI or action.id in _TERMINAL_ACTION_IDS:
            exit_code = self._run_terminal(argv)
            if exit_code != 0:
                self.console.print(f"[red]{action.label} exited {exit_code}[/red]")
            return
        result = self._run_captured(argv)
        _print_result(self.console, result)

    def _run_argv(self, argv: Sequence[str]) -> CommandResult:
        """Helper for tests: run an arbitrary argv through the captured path."""
        return self._run_captured(argv)

    # -- main loop ---------------------------------------------------------

    def run(self) -> None:
        self._running = True
        self._print_banner()
        self._maybe_show_first_run_tour()
        self._print_overview()
        while self._running:
            try:
                line = self._prompt("factory> ").strip()
            except (KeyboardInterrupt, EOFError):
                self.console.print()
                self._running = False
                break
            if not line:
                continue
            if line.startswith("/"):
                self._handle_slash(line)
                continue
            self.handle_command(line)

    def handle_command(self, line: str) -> None:
        action = resolve_action(line)
        if action is None:
            self.console.print(f"[red]Unknown command:[/red] {line}. Try [cyan]/help[/cyan].")
            self._suggest_similar(line)
            return
        # Actions declared as PROJECT-only require a selection first.
        if action.mode is ActionMode.PROJECT and self.context.selected is None:
            self.console.print(
                f"[yellow]{action.label} needs a project selected. Try /project <name>.[/yellow]"
            )
            return
        self._run_action(action)

    def _suggest_similar(self, query: str) -> None:
        query = query.lower()
        hits = [a.id for a in ACTIONS if query in a.id.lower()][:5]
        if hits:
            self.console.print("  Did you mean:  " + ", ".join(hits))


def _wordlist_completer(choices: Sequence[str]):
    from prompt_toolkit.completion import WordCompleter

    return WordCompleter(list(choices), ignore_case=True)


def _print_result(console: Console, result: CommandResult) -> None:
    if result.stdout.strip():
        console.print(result.stdout.rstrip())
    if result.stderr.strip():
        console.print("[dim]--- stderr ---[/dim]")
        console.print(result.stderr.rstrip())
    if not result.stdout.strip() and not result.stderr.strip():
        console.print("[dim](no output)[/dim]")
    if not result.ok:
        console.print(f"[red]exit {result.exit_code}[/red]")


def run_shell(preselected: Optional[Path] = None) -> int:
    """Entry point used by ``factory shell``. Returns a process exit code."""
    context = ShellContext.load(preselected=preselected)
    FactoryRepl(context).run()
    return 0
