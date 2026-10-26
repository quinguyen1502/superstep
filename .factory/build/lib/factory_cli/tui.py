from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from threading import Event
from time import monotonic
from typing import Any, Callable, Dict, Generic, List, Optional, Tuple, TypeVar

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.suggester import SuggestFromList
from textual.widgets import (
    Button,
    Collapsible,
    DataTable,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    LoadingIndicator,
    MarkdownViewer,
    Select,
    SelectionList,
    Static,
    TabbedContent,
    TabPane,
    TextArea,
)

from .clarification import Clarification, save_clarification
from .constants import TASK_STATES, TOOL_IDS
from .guidance import (
    PROJECT_PRESETS,
    REFINEMENT_SECTIONS,
    analyze_compatibility,
    command_suggestions,
)
from .models import ImportPlan, ProjectIntake, RefinementSettings, TechChoice
from .project import atomic_write
from .scaffold.models import ScaffoldOutput, ScaffoldPublishPlan
from .spec_sections import changed_sections, merge_sections, parse_sections
from .stacks import find_stack, stack_suggestions, stacks_for_area
from .tooling import CommandPolicy, ToolPolicy


APP_CSS = """
Screen { background: $surface; }
#form-tabs, #import-tabs, #review, #questionnaire, #refinement-config { height: 1fr; }
#section-review-tabs { height: 1fr; }
.tab-scroll, #questionnaire { padding: 1 2; }
.tab-scroll { height: 1fr; }
.section { margin: 1 0; padding: 1; border: round $primary 40%; }
.section-title {
    height: 3;
    margin-top: 1;
    padding: 0 1;
    border-left: thick $primary;
    background: $boost;
    content-align: left middle;
    text-style: bold;
}
.section-help { color: $text-muted; margin: 0 1 1 1; }
.field-label { margin-top: 1; text-style: bold; }
.field-help { color: $text-muted; margin-bottom: 1; }
.help { color: $text-muted; margin-bottom: 1; }
.error { color: $error; margin: 1 0; }
Input, Select, TextArea, SelectionList { margin-bottom: 1; }
.tech-row { height: auto; margin-bottom: 1; }
.tech-row .tech-choice { width: 1fr; margin: 0 1 0 0; }
.tech-row .tech-status { width: 20; margin: 0; }
.tech-custom { margin-bottom: 1; }
.insights {
    margin: 1 0;
    padding: 1 2;
    border: round $secondary 40%;
    background: $boost;
}
.refinement-sections { margin: 0 0 1 0; max-height: 9; }
.optional-section { margin: 1 0; }
TextArea { height: 6; }
SelectionList { height: auto; max-height: 10; }
#actions { height: 3; align: right middle; background: $surface; padding-right: 1; }
#actions Button { margin-left: 1; }
#actions.three-actions {
    layout: grid;
    grid-size: 3 1;
    grid-columns: 1fr 1fr 1fr;
    grid-gutter: 0 1;
    padding: 0 1;
}
#actions.three-actions Button { width: 1fr; min-width: 0; margin: 0; }
#actions.two-actions {
    layout: grid;
    grid-size: 2 1;
    grid-columns: 1fr 1fr;
    grid-gutter: 0 1;
    padding: 0 1;
}
#actions.two-actions Button { width: 1fr; min-width: 0; margin: 0; }
#review { padding: 0 1; }
#refinement-body { height: 1fr; align: center middle; }
#refinement-card { width: 70; max-width: 90%; height: auto; padding: 2 3; border: round $primary; }
#refinement-title { text-style: bold; text-align: center; }
#refinement-spinner { height: 3; margin: 1 0; }
#refinement-status, #refinement-elapsed, #refinement-safety { text-align: center; }
#refinement-safety { color: $text-muted; margin-top: 1; }
.conditional-hidden { display: none; }
#board { height: 1fr; }
.board-column { width: 1fr; height: 1fr; border: round $primary 40%; margin: 0 1; }
.board-column-title {
    height: 3;
    padding: 0 1;
    background: $boost;
    text-style: bold;
    content-align: center middle;
}
.board-column-body { height: 1fr; padding: 0 1; }
.task-card { width: 1fr; height: auto; margin: 1 0; text-align: left; }
.task-card.moved { border-left: thick $warning; }
.board-empty { color: $text-muted; padding: 1; }
#board-status { height: 1; padding: 0 1; background: $boost; color: $text-muted; }
#board-status.dirty { color: $warning; text-style: bold; }
TaskDetailScreen { align: center middle; }
#task-detail {
    width: 90%;
    height: 90%;
    border: round $primary;
    background: $surface;
}
#task-detail-body { height: 1fr; padding: 0 1; }
#dashboard { height: 1fr; padding: 0 1; }
.dashboard-title { text-style: bold; margin: 1 0; }
#kpi-row { height: auto; margin: 1 0; }
.kpi { width: 1fr; height: 5; border: round $primary 40%; padding: 0 1; margin: 0 1; }
.kpi-label { color: $text-muted; }
.kpi-value { text-style: bold; }
.kpi-delta { color: $text-muted; }
.kpi.alert { border: round $error; }
.kpi.alert .kpi-value { color: $error; }
.chart { padding: 0 1; margin-bottom: 1; }
.dash-chart { height: 14; margin-bottom: 1; }
.over-budget { color: $error; text-style: bold; }
#projects-list { height: 1fr; padding: 0 1; }
"""


PROJECT_FIELDS: Dict[str, Tuple[str, str, str]] = {
    "project-name": (
        "Project name",
        "A stable name used in generated artifacts and the project directory.",
        "e.g. Customer Support Portal",
    ),
    "description": (
        "One-line description",
        "Summarize the product, target user, and main value in one sentence.",
        "e.g. A portal that helps support teams resolve requests faster",
    ),
    "problem": (
        "Problem statement",
        "Describe the current pain, who experiences it, and why it matters.",
        "What is difficult today, for whom, and with what impact?",
    ),
    "outcome": (
        "Intended outcome",
        "Describe the observable change that would make this project successful.",
        "What should become possible or measurably better?",
    ),
    "users": (
        "Primary users",
        "List the main user groups and the jobs they need to complete.",
        "User group — primary need",
    ),
    "goals": (
        "Goals",
        "List the outcomes the project must achieve, preferably as testable statements.",
        "One goal per line",
    ),
    "non-goals": (
        "Non-goals",
        "Call out adjacent outcomes this project intentionally does not optimize for.",
        "One non-goal per line",
    ),
    "mvp": (
        "MVP scope",
        "Define the smallest coherent release that delivers value to primary users.",
        "Capabilities required for the first usable release",
    ),
    "post-mvp": (
        "Post-MVP scope",
        "Capture valuable follow-up capabilities that should not delay the MVP.",
        "Likely capabilities after the first release",
    ),
    "out-of-scope": (
        "Out of scope",
        "State hard boundaries that must not be included in the current plan.",
        "Explicit exclusions and deferred areas",
    ),
    "flows": (
        "Core flows",
        "Describe the essential end-to-end journeys from trigger to outcome.",
        "Actor → action → system response → result",
    ),
    "constraints": (
        "Constraints",
        "Record non-negotiable business, security, compliance, budget, or platform limits.",
        "Constraint — reason or impact",
    ),
    "integrations": (
        "Integrations",
        "List external systems, APIs, identity providers, and data exchanges.",
        "System — data exchanged — known constraints",
    ),
    "raw-draft": (
        "Raw notes or draft",
        "Paste any existing notes. Factory keeps them as source context for refinement.",
        "Unstructured ideas, links, assumptions, or a draft specification",
    ),
}


TECH_FIELD_HINTS: Dict[str, Tuple[str, str]] = {
    "frontend": (
        "Web UI technology, language, and client-side architecture.",
        "e.g. React + TypeScript",
    ),
    "mobile": (
        "Native or cross-platform mobile direction; leave blank if not applicable.",
        "e.g. Flutter",
    ),
    "backend": (
        "Server runtime, framework, and API style.",
        "e.g. Python + FastAPI + REST",
    ),
    "database": (
        "Primary data stores and important persistence constraints.",
        "e.g. PostgreSQL 17",
    ),
    "infrastructure": (
        "Cloud, hosting, networking, and infrastructure-as-code direction.",
        "e.g. AWS + Terraform",
    ),
    "ci_cd": (
        "Continuous integration and delivery automation.",
        "e.g. GitHub Actions",
    ),
    "deployment": (
        "Build, release, and runtime delivery approach.",
        "e.g. GitHub Actions + ECS",
    ),
    "testing": ("Test frameworks and the expected testing layers.", "e.g. pytest + Playwright"),
}


TECH_SUGGESTIONS: Dict[str, Tuple[str, ...]] = stack_suggestions()


COMMAND_FIELD_HINTS: Dict[str, Tuple[str, str]] = {
    "install": ("Install project dependencies.", "e.g. npm ci"),
    "run": ("Start the project for local development.", "e.g. npm run dev"),
    "test": ("Run the automated test suite.", "e.g. npm test"),
    "build": ("Produce a distributable or deployable build.", "e.g. npm run build"),
    "lint": ("Run static lint checks.", "e.g. npm run lint"),
    "typecheck": ("Run static type checking.", "e.g. npm run typecheck"),
    "format": ("Apply or verify code formatting.", "e.g. npm run format"),
    "migration": ("Apply database schema migrations.", "e.g. alembic upgrade head"),
}


COMMAND_SUGGESTIONS: Dict[str, Tuple[str, ...]] = {
    "install": ("npm ci", "pnpm install --frozen-lockfile", "pip install -e ."),
    "run": ("npm run dev", "uvicorn app.main:app --reload", "make run"),
    "test": ("npm test", "pytest", "make test"),
    "build": ("npm run build", "python -m build", "make build"),
    "lint": ("npm run lint", "ruff check .", "make lint"),
    "typecheck": ("npm run typecheck", "mypy .", "pyright"),
    "format": ("npm run format", "ruff format .", "make format"),
    "migration": ("alembic upgrade head", "npm run migrate", "make migrate"),
}


STACK_STATUS_OPTIONS = (
    ("Approved — owner confirmed", "Approved"),
    ("Preferred — current direction", "Preferred"),
    ("Proposed — needs review", "Proposed"),
    ("Unknown — undecided", "Unknown"),
)


OTHER_TECH_VALUE = "__other__"

ReturnType = TypeVar("ReturnType")


class FactoryApp(App[ReturnType], Generic[ReturnType]):
    """Factory TUI base with a light default and an optional theme toggle."""

    BINDINGS = [("ctrl+t", "toggle_dark", "Toggle theme")]

    def __init__(self) -> None:
        super().__init__()
        self.theme = "textual-light"


def _section_header(
    title: str, description: str, section_id: str
) -> Tuple[Static, Static]:
    return (
        Static(title, classes="section-title"),
        Static(description, id=f"section-help-{section_id}", classes="section-help"),
    )


def _field_header(label: str, hint: str, widget_id: str) -> Tuple[Label, Static]:
    return (
        Label(label, classes="field-label"),
        Static(hint, id=f"help-{widget_id}", classes="field-help"),
    )


def _text_area(value: str, widget_id: str, placeholder: str = "") -> TextArea:
    return TextArea(
        value,
        id=widget_id,
        placeholder=placeholder,
        tooltip=PROJECT_FIELDS[widget_id][1],
    )


class ProjectWizardApp(FactoryApp[Optional[ProjectIntake]]):
    CSS = APP_CSS
    TITLE = "AI Software Factory - Project Setup"

    def __init__(
        self,
        intake: ProjectIntake,
        save_path: Optional[Path] = None,
        tool_availability: Optional[Dict[str, bool]] = None,
    ) -> None:
        super().__init__()
        self.intake = intake
        self.save_path = save_path
        self.tool_availability = tool_availability or {}
        self.saved = False

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="tab-overview", id="form-tabs"):
            with TabPane("Overview", id="tab-overview"):
                with VerticalScroll(classes="tab-scroll"):
                    yield from _section_header(
                        "Project intent",
                        "Define the problem, users, and intended outcome. Known decisions "
                        "and uncertainty are both useful inputs.",
                        "intent",
                    )
                    yield from _field_header(
                        "Starter preset",
                        "Optionally fill blank technology and command fields with Proposed "
                        "starter values. Presets never overwrite owner input.",
                        "project-preset",
                    )
                    yield Select(
                        [
                            (
                                f"{preset['label']} — {preset['description']}",
                                preset_id,
                            )
                            for preset_id, preset in PROJECT_PRESETS.items()
                        ],
                        value=self.intake.project_preset or Select.NULL,
                        allow_blank=True,
                        id="project-preset",
                    )
                    yield Static(
                        "No preset selected; all fields remain owner-defined.",
                        id="preset-help",
                        classes="field-help",
                    )
                    yield from self.compose_input_field(
                        "project-name", self.intake.project_name
                    )
                    yield from self.compose_input_field(
                        "description", self.intake.one_line_description
                    )
                    yield from self.compose_text_field(
                        "problem", self.intake.problem_statement
                    )
                    yield from self.compose_text_field(
                        "outcome", self.intake.intended_outcome
                    )
                    yield from self.compose_text_field("users", self.intake.primary_users)

            with TabPane("Scope & Flows", id="tab-scope"):
                with VerticalScroll(classes="tab-scroll"):
                    yield from _section_header(
                        "Scope and flows",
                        "Separate the first useful release from later work, then describe "
                        "its essential end-to-end journeys.",
                        "scope",
                    )
                    yield from self.compose_text_field("goals", self.intake.goals)
                    yield from self.compose_text_field(
                        "non-goals", self.intake.non_goals
                    )
                    yield from self.compose_text_field("mvp", self.intake.mvp_scope)
                    yield from self.compose_optional_text_field(
                        "post-mvp", self.intake.post_mvp_scope
                    )
                    yield from self.compose_text_field(
                        "out-of-scope", self.intake.out_of_scope
                    )
                    yield from self.compose_text_field("flows", self.intake.core_flows)

            with TabPane("Technology", id="tab-technology"):
                with VerticalScroll(classes="tab-scroll"):
                    yield from self.compose_tools()
                    yield from self.compose_technology()

            with TabPane("Delivery", id="tab-delivery"):
                with VerticalScroll(classes="tab-scroll"):
                    yield from _section_header(
                        "Delivery context",
                        "Capture constraints, integrations, expected commands, and any "
                        "source notes agents must preserve.",
                        "delivery",
                    )
                    yield from self.compose_text_field(
                        "constraints", self.intake.constraints
                    )
                    yield from self.compose_optional_text_field(
                        "integrations", self.intake.integrations
                    )
                    yield from self.compose_commands()
                    yield from self.compose_optional_text_field(
                        "raw-draft", self.intake.raw_draft
                    )

        yield Static("", id="error", classes="error")
        with Horizontal(
            id="actions",
            classes="three-actions" if self.save_path is not None else "",
        ):
            yield Button("Cancel", id="cancel")
            if self.save_path is not None:
                yield Button("Save draft", id="save-draft")
            yield Button("Review draft", id="continue", variant="primary")
        yield Footer()

    def compose_input_field(self, widget_id: str, value: str) -> ComposeResult:
        label, hint, placeholder = PROJECT_FIELDS[widget_id]
        yield from _field_header(label, hint, widget_id)
        yield Input(
            value,
            id=widget_id,
            placeholder=placeholder,
            tooltip=hint,
        )

    def compose_text_field(self, widget_id: str, value: str) -> ComposeResult:
        label, hint, placeholder = PROJECT_FIELDS[widget_id]
        yield from _field_header(label, hint, widget_id)
        yield _text_area(value, widget_id, placeholder)

    def compose_optional_text_field(self, widget_id: str, value: str) -> ComposeResult:
        label, hint, placeholder = PROJECT_FIELDS[widget_id]
        with Collapsible(
            title=label,
            collapsed=not bool(value.strip()),
            id=f"optional-{widget_id}",
            classes="optional-section",
        ):
            yield Static(hint, id=f"help-{widget_id}", classes="field-help")
            yield _text_area(value, widget_id, placeholder)

    def compose_tools(self) -> ComposeResult:
        yield from _section_header(
            "AI coding tools",
            "Choose which local AI CLIs receive project instructions. Refinement is "
            "configured after reviewing the draft.",
            "tools",
        )
        yield from _field_header(
            "Enabled tools",
            "Instruction bridges are generated only for selected tools. Availability "
            "describes this machine.",
            "tools",
        )
        yield SelectionList[str](
            *[
                (self.tool_label(tool_id), tool_id, tool_id in self.intake.tools)
                for tool_id in TOOL_IDS
            ],
            id="tools",
        )

    def compose_technology(self) -> ComposeResult:
        yield from _section_header(
            "Technology direction",
            "Choose a common option or select Other to enter a custom technology, "
            "then record its decision status explicitly.",
            "technology",
        )
        for area, choice in self.intake.tech_stack.items():
            hint, placeholder = TECH_FIELD_HINTS.get(
                area,
                ("Technology direction for this project layer.", "Technology or approach"),
            )
            suggestions = TECH_SUGGESTIONS.get(area, ())
            suggestion_hint = (
                f"{hint} Choose a listed option or select Other for a custom value."
                if suggestions
                else hint
            )
            yield from _field_header(
                area.replace("_", " ").title(), suggestion_hint, f"tech-{area}"
            )
            if not choice.value:
                selected_value = Select.NULL
            elif find_stack(area, choice.value) is not None:
                selected_value = find_stack(area, choice.value).label
            else:
                selected_value = OTHER_TECH_VALUE
            definitions = {stack.label: stack for stack in stacks_for_area(area)}
            with Horizontal(classes="tech-row", id=f"tech-row-{area}"):
                yield Select(
                    [
                        (definitions[value].option_label, value)
                        for value in suggestions
                    ]
                    + [("Other…", OTHER_TECH_VALUE)],
                    value=selected_value,
                    allow_blank=True,
                    id=f"tech-choice-{area}",
                    classes="tech-choice",
                )
                yield Select(
                    list(STACK_STATUS_OPTIONS),
                    value=choice.status,
                    allow_blank=False,
                    id=f"status-{area}",
                    classes="tech-status",
                )
            custom_input = Input(
                choice.value if selected_value == OTHER_TECH_VALUE else "",
                id=f"tech-other-{area}",
                placeholder=placeholder,
                tooltip=f"Custom {area.replace('_', ' ')} technology",
                classes="tech-custom",
            )
            custom_input.display = selected_value == OTHER_TECH_VALUE
            yield custom_input
            selected_stack = (
                find_stack(area, choice.value) if choice.value else None
            )
            yield Static(
                selected_stack.capability_summary if selected_stack else "",
                id=f"tech-capability-{area}",
                classes="field-help",
            )
        yield from _section_header(
            "Architecture and compatibility insights",
            "Deterministic rules explain likely boundaries and flag combinations that "
            "need confirmation. Insights never block the form.",
            "compatibility",
        )
        yield Static(
            "Select technologies to see architecture and compatibility insights.",
            id="compatibility-insights",
            classes="insights",
        )

    def compose_commands(self) -> ComposeResult:
        yield from _section_header(
            "Expected commands",
            "Record commands agents may try later. Suggestions remain Expected until "
            "repository evidence makes them Observed.",
            "commands",
        )
        for name, command in self.intake.commands.items():
            hint, placeholder = COMMAND_FIELD_HINTS.get(
                name, ("Expected project command.", "Command to verify later")
            )
            dynamic = command_suggestions(self.intake.tech_stack).get(name, ())
            suggestions = tuple(dict.fromkeys(dynamic + COMMAND_SUGGESTIONS.get(name, ())))
            suggestion_hint = (
                f"{hint} Suggestions: {', '.join(suggestions)}. Free text is allowed."
                if suggestions
                else hint
            )
            yield from _field_header(
                name.replace("_", " ").title(), suggestion_hint, f"command-{name}"
            )
            yield Input(
                command,
                id=f"command-{name}",
                placeholder=placeholder,
                tooltip=suggestion_hint,
                suggester=(
                    SuggestFromList(suggestions, case_sensitive=False)
                    if suggestions
                    else None
                ),
            )

    def tool_label(self, tool_id: str) -> str:
        if tool_id not in self.tool_availability:
            return tool_id
        status = "available" if self.tool_availability[tool_id] else "CLI not found"
        return f"{tool_id} ({status})"

    def collect(self) -> ProjectIntake:
        tools = list(self.query_one("#tools", SelectionList).selected)
        refiner = self.intake.refiner if self.intake.refiner in tools else None
        stack: Dict[str, TechChoice] = {}
        for area in self.intake.tech_stack:
            status_value = self.query_one(f"#status-{area}", Select).value
            selected_value = self.query_one(f"#tech-choice-{area}", Select).value
            if selected_value is Select.NULL:
                technology = ""
            elif selected_value == OTHER_TECH_VALUE:
                technology = self.query_one(f"#tech-other-{area}", Input).value.strip()
                if not technology:
                    raise ValueError(
                        f"{area.replace('_', ' ').title()} requires a custom technology."
                    )
            else:
                technology = str(selected_value)
            stack[area] = TechChoice(
                value=technology,
                status=str(status_value),
            )
        commands = {
            name: self.query_one(f"#command-{name}", Input).value.strip()
            for name in self.intake.commands
        }
        preset_value = self.query_one("#project-preset", Select).value
        result = ProjectIntake(
            project_name=self.query_one("#project-name", Input).value.strip(),
            project_preset=(
                "" if preset_value is Select.NULL else str(preset_value)
            ),
            one_line_description=self.query_one("#description", Input).value.strip(),
            problem_statement=self.query_one("#problem", TextArea).text.strip(),
            intended_outcome=self.query_one("#outcome", TextArea).text.strip(),
            primary_users=self.query_one("#users", TextArea).text.strip(),
            goals=self.query_one("#goals", TextArea).text.strip(),
            non_goals=self.query_one("#non-goals", TextArea).text.strip(),
            mvp_scope=self.query_one("#mvp", TextArea).text.strip(),
            post_mvp_scope=self.query_one("#post-mvp", TextArea).text.strip(),
            out_of_scope=self.query_one("#out-of-scope", TextArea).text.strip(),
            core_flows=self.query_one("#flows", TextArea).text.strip(),
            constraints=self.query_one("#constraints", TextArea).text.strip(),
            integrations=self.query_one("#integrations", TextArea).text.strip(),
            raw_draft=self.query_one("#raw-draft", TextArea).text.strip(),
            tools=tools,
            refiner=refiner,
            use_ai=False,
            refinement_sections=list(self.intake.refinement_sections or ["all"]),
            refinement_timeout_seconds=self.intake.refinement_timeout_seconds,
            tech_stack=stack,
            commands=commands,
            refinement=dict(self.intake.refinement),
        )
        result.validate()
        return result

    @on(Select.Changed, ".tech-choice")
    def technology_choice_changed(self, event: Select.Changed) -> None:
        select_id = event.select.id or ""
        area = select_id.replace("tech-choice-", "", 1)
        self.query_one(f"#tech-other-{area}", Input).display = (
            event.value == OTHER_TECH_VALUE
        )
        self.call_after_refresh(self.refresh_technology_guidance)

    @on(Input.Changed, ".tech-custom")
    def custom_technology_changed(self, _event: Input.Changed) -> None:
        self.call_after_refresh(self.refresh_technology_guidance)

    @on(Select.Changed, "#project-preset")
    def project_preset_changed(self, event: Select.Changed) -> None:
        if event.value is Select.NULL:
            self.query_one("#preset-help", Static).update(
                "No preset selected; existing values are preserved."
            )
            return
        preset_id = str(event.value)
        preset = PROJECT_PRESETS[preset_id]
        self.query_one("#preset-help", Static).update(
            f"{preset['label']}: {preset['description']} Only blank fields are filled."
        )
        for area, value in dict(preset["tech_stack"]).items():
            select = self.query_one(f"#tech-choice-{area}", Select)
            if select.value is not Select.NULL:
                continue
            suggestions = TECH_SUGGESTIONS.get(area, ())
            if value in suggestions:
                select.value = value
            else:
                select.value = OTHER_TECH_VALUE
                self.query_one(f"#tech-other-{area}", Input).value = str(value)
            self.query_one(f"#status-{area}", Select).value = "Proposed"
        for name, value in dict(preset["commands"]).items():
            command = self.query_one(f"#command-{name}", Input)
            if not command.value.strip():
                command.value = str(value)
        self.call_after_refresh(self.refresh_technology_guidance)

    def current_stack(self) -> Dict[str, TechChoice]:
        stack: Dict[str, TechChoice] = {}
        for area in self.intake.tech_stack:
            selected = self.query_one(f"#tech-choice-{area}", Select).value
            if selected is Select.NULL:
                value = ""
            elif selected == OTHER_TECH_VALUE:
                value = self.query_one(f"#tech-other-{area}", Input).value.strip()
            else:
                value = str(selected)
            stack[area] = TechChoice(
                value,
                str(self.query_one(f"#status-{area}", Select).value),
            )
        return stack

    def refresh_technology_guidance(self) -> None:
        stack = self.current_stack()
        for area, choice in stack.items():
            definition = find_stack(area, choice.value)
            self.query_one(f"#tech-capability-{area}", Static).update(
                definition.capability_summary if definition else "Custom technology; automation support must be discovered."
            )
        preview = ProjectIntake(
            project_name=self.intake.project_name or "preview",
            goals=self.query_one("#goals", TextArea).text,
            mvp_scope=self.query_one("#mvp", TextArea).text,
            core_flows=self.query_one("#flows", TextArea).text,
            tech_stack=stack,
        )
        insights = analyze_compatibility(preview)
        if insights:
            lines = []
            for insight in insights:
                icon = "⚠" if insight.level == "warning" else "ℹ"
                lines.append(f"{icon} {insight.title}: {insight.message}")
                if insight.recommendation:
                    lines.append(f"  Suggested: {insight.recommendation}")
            content = "\n".join(lines)
        elif any(choice.value for choice in stack.values()):
            content = "✓ No deterministic compatibility warnings for the current selections."
        else:
            content = "Select technologies to see architecture and compatibility insights."
        self.query_one("#compatibility-insights", Static).update(content)

        dynamic = command_suggestions(stack)
        for name in self.intake.commands:
            suggestions = tuple(
                dict.fromkeys(dynamic.get(name, ()) + COMMAND_SUGGESTIONS.get(name, ()))
            )
            hint, _placeholder = COMMAND_FIELD_HINTS[name]
            suggestion_hint = (
                f"{hint} Stack-aware suggestions: {', '.join(suggestions)}. "
                "Free text is allowed; values remain Expected."
            )
            self.query_one(f"#help-command-{name}", Static).update(suggestion_hint)
            self.query_one(f"#command-{name}", Input).suggester = SuggestFromList(
                suggestions, case_sensitive=False
            )

    def on_mount(self) -> None:
        self.refresh_technology_guidance()

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.exit(None)

    @on(Button.Pressed, "#save-draft")
    def save_draft(self) -> None:
        try:
            intake = self.collect()
        except ValueError as exc:
            self.show_validation_error(str(exc))
            return
        if self.save_path is None:
            return
        atomic_write(self.save_path, intake.to_yaml())
        self.saved = True
        self.exit(None)

    @on(Button.Pressed, "#continue")
    def continue_to_review(self) -> None:
        try:
            intake = self.collect()
        except ValueError as exc:
            self.show_validation_error(str(exc))
            return
        self.exit(intake)

    def show_validation_error(self, message: str) -> None:
        tab = "tab-overview"
        lowered = message.lower()
        if any(word in lowered for word in ("tool", "refiner", "technology", "ai")):
            tab = "tab-technology"
        self.query_one("#form-tabs", TabbedContent).active = tab
        self.query_one("#error", Static).update(message)


class ReviewApp(FactoryApp[bool]):
    CSS = APP_CSS
    TITLE = "AI Software Factory - Review"

    def __init__(self, markdown: str, accept_label: str = "Apply") -> None:
        super().__init__()
        self.markdown = markdown
        self.accept_label = accept_label

    def compose(self) -> ComposeResult:
        yield Header()
        yield MarkdownViewer(
            self.markdown,
            show_table_of_contents=False,
            id="review",
        )
        with Horizontal(id="actions"):
            yield Button("Cancel", id="cancel")
            yield Button(self.accept_label, id="accept", variant="success")
        yield Footer()

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.exit(False)

    @on(Button.Pressed, "#accept")
    def accept(self) -> None:
        self.exit(True)


class DraftReviewApp(FactoryApp[Optional[str]]):
    CSS = APP_CSS
    TITLE = "AI Software Factory - Draft Review"

    def __init__(self, markdown: str, can_refine: bool = True) -> None:
        super().__init__()
        self.markdown = markdown
        self.can_refine = can_refine

    def compose(self) -> ComposeResult:
        yield Header()
        yield MarkdownViewer(
            self.markdown,
            show_table_of_contents=False,
            id="review",
        )
        with Horizontal(id="actions", classes="three-actions"):
            yield Button("Cancel", id="cancel")
            yield Button("Publish as-is", id="publish-draft", variant="success")
            refine = Button("Refine with AI", id="configure-refinement", variant="primary")
            refine.disabled = not self.can_refine
            yield refine
        yield Footer()

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.exit(None)

    @on(Button.Pressed, "#publish-draft")
    def publish_draft(self) -> None:
        self.exit("publish")

    @on(Button.Pressed, "#configure-refinement")
    def configure_refinement(self) -> None:
        self.exit("refine")


class RefinementConfigApp(FactoryApp[Optional[RefinementSettings]]):
    CSS = APP_CSS
    TITLE = "AI Software Factory - Refinement Configuration"

    def __init__(
        self,
        enabled_tools: List[str],
        default_refiner: Optional[str],
        sections: List[str],
        timeout_seconds: int,
        tool_availability: Optional[Dict[str, bool]] = None,
    ) -> None:
        super().__init__()
        self.enabled_tools = enabled_tools
        self.default_refiner = (
            default_refiner
            if default_refiner in enabled_tools
            else enabled_tools[0] if enabled_tools else None
        )
        self.sections = sections or ["all"]
        self.timeout_seconds = timeout_seconds
        self.tool_availability = tool_availability or {}

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="refinement-config", classes="tab-scroll"):
            yield from _section_header(
                "Refinement configuration",
                "Choose how AI may improve this draft. No project files are changed "
                "until the final review is accepted.",
                "refinement-config",
            )
            yield from _field_header(
                "AI tool",
                "Factory uses exactly this local CLI and never falls back silently.",
                "refinement-tool",
            )
            yield Select(
                [
                    (self.tool_label(tool_id), tool_id)
                    for tool_id in self.enabled_tools
                ],
                value=self.default_refiner or Select.NULL,
                allow_blank=False,
                id="refinement-tool",
            )
            yield from _field_header(
                "Sections",
                "Choose the entire specification or section groups AI may change. "
                "Changes are reviewed section by section afterward.",
                "refinement-sections",
            )
            yield SelectionList[str](
                *[
                    (label, section_id, section_id in self.sections)
                    for section_id, (label, _headings) in REFINEMENT_SECTIONS.items()
                ],
                id="refinement-sections",
                classes="refinement-sections",
            )
            yield from _field_header(
                "Timeout in seconds",
                "Maximum time allowed for the local AI CLI before the deterministic "
                "draft is preserved.",
                "refinement-timeout",
            )
            yield Input(
                str(self.timeout_seconds),
                id="refinement-timeout",
                placeholder="300",
            )
            yield Static("", id="refinement-error", classes="error")
        with Horizontal(id="actions"):
            yield Button("Back", id="back")
            yield Button("Start refinement", id="start-refinement", variant="primary")
        yield Footer()

    def tool_label(self, tool_id: str) -> str:
        if tool_id not in self.tool_availability:
            return tool_id
        status = "available" if self.tool_availability[tool_id] else "CLI not found"
        return f"{tool_id} ({status})"

    @on(Button.Pressed, "#back")
    def back(self) -> None:
        self.exit(None)

    @on(Button.Pressed, "#start-refinement")
    def start_refinement(self) -> None:
        try:
            tool_value = self.query_one("#refinement-tool", Select).value
            if tool_value is Select.NULL:
                raise ValueError("Select an AI tool.")
            sections = list(
                self.query_one("#refinement-sections", SelectionList).selected
            )
            if "all" in sections:
                sections = ["all"]
            timeout_text = self.query_one("#refinement-timeout", Input).value.strip()
            try:
                timeout_seconds = int(timeout_text)
            except ValueError as exc:
                raise ValueError(
                    "Refinement timeout must be a positive integer."
                ) from exc
            settings = RefinementSettings(
                tool_id=str(tool_value),
                sections=sections,
                timeout_seconds=timeout_seconds,
            )
            settings.validate()
        except (ValueError, TypeError) as exc:
            message = "Refinement timeout must be a positive integer."
            if isinstance(exc, ValueError) and str(exc):
                message = str(exc)
            self.query_one("#refinement-error", Static).update(message)
            return
        self.exit(settings)


class SectionReviewApp(FactoryApp[str]):
    """Accept or reject AI changes at level-two specification boundaries."""

    CSS = APP_CSS
    TITLE = "AI Software Factory - Refinement Review"

    def __init__(
        self,
        baseline: str,
        refined: str,
        allowed_headings: Optional[Tuple[str, ...]] = None,
    ) -> None:
        super().__init__()
        self.baseline = baseline
        self.refined = refined
        self.allowed_headings = allowed_headings
        self.changed = changed_sections(
            baseline,
            refined,
            allowed_headings if allowed_headings else None,
        )
        self.accepted_sections: List[str] = []
        self.rejected_sections: List[str] = []

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="section-choices", id="section-review-tabs"):
            with TabPane("Section choices", id="section-choices"):
                with VerticalScroll(classes="tab-scroll"):
                    yield Static(
                        "Select AI-refined sections to apply. Unselected sections remain "
                        "exactly as generated by the deterministic renderer.",
                        classes="section-help",
                    )
                    if self.changed:
                        yield SelectionList[str](
                            *[
                                (f"{heading} — changed", heading, True)
                                for heading in self.changed
                            ],
                            id="refined-section-choices",
                        )
                        yield MarkdownViewer(
                            self.render_change_summary(),
                            show_table_of_contents=False,
                            id="section-change-summary",
                        )
                    else:
                        yield Static(
                            "The AI returned no eligible section changes.",
                            classes="insights",
                        )
            with TabPane("Proposed document", id="section-proposed"):
                yield MarkdownViewer(
                    self.refined,
                    show_table_of_contents=False,
                    id="section-proposed-viewer",
                )
        with Horizontal(id="actions"):
            yield Button("Use deterministic", id="use-deterministic")
            yield Button("Apply selected sections", id="apply-sections", variant="success")
        yield Footer()

    def render_change_summary(self) -> str:
        before = parse_sections(self.baseline)
        after = parse_sections(self.refined)
        lines = ["# AI section changes", ""]
        for heading in self.changed:
            before_size = len(before.sections.get(heading, "").splitlines())
            after_size = len(after.sections.get(heading, "").splitlines())
            lines.extend(
                (
                    f"## {heading}",
                    "",
                    f"- Deterministic: {before_size} lines",
                    f"- AI proposal: {after_size} lines",
                    "- Selected by default; deselect to preserve deterministic content.",
                    "",
                )
            )
        return "\n".join(lines)

    @on(Button.Pressed, "#use-deterministic")
    def use_deterministic(self) -> None:
        self.accepted_sections = []
        self.rejected_sections = list(self.changed)
        self.exit(self.baseline)

    @on(Button.Pressed, "#apply-sections")
    def apply_sections(self) -> None:
        if self.changed:
            selected = list(
                self.query_one("#refined-section-choices", SelectionList).selected
            )
        else:
            selected = []
        self.accepted_sections = selected
        self.rejected_sections = [
            heading for heading in self.changed if heading not in selected
        ]
        self.exit(merge_sections(self.baseline, self.refined, selected))


class ImportReviewApp(FactoryApp[Optional[Dict[str, str]]]):
    CSS = APP_CSS
    TITLE = "AI Software Factory - Import Review"

    def __init__(self, plan: ImportPlan, project_dir: Path, markdown: str) -> None:
        super().__init__()
        self.plan = plan
        self.project_dir = project_dir
        self.markdown = markdown

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="import-preview", id="import-tabs"):
            with TabPane("Preview", id="import-preview"):
                yield MarkdownViewer(
                    self.markdown,
                    show_table_of_contents=False,
                    id="import-preview-viewer",
                )
            with TabPane("Conflict resolution", id="import-conflicts"):
                with VerticalScroll(classes="tab-scroll"):
                    if self.plan.conflicts:
                        yield Static("Conflict resolution", classes="section")
                        yield Static(
                            "Skip preserves the existing file and saves a proposal. "
                            "Merge publishes only content reviewed below.",
                            classes="help",
                        )
                    else:
                        yield Static(
                            "No conflicts were detected. Existing files remain untouched.",
                            classes="section",
                        )
                    for index, action in enumerate(self.plan.conflicts):
                        yield Label(action.path, classes="field-label")
                        yield Select(
                            [
                                ("Skip; keep existing and save proposal", "skip"),
                                ("Publish reviewed merge", "merge"),
                            ],
                            value="skip",
                            allow_blank=False,
                            id=f"import-resolution-{index}",
                        )
                        existing = (self.project_dir / action.path).read_text(
                            encoding="utf-8"
                        )
                        yield TextArea(existing, id=f"import-merge-{index}")
        with Horizontal(id="actions"):
            yield Button("Cancel", id="cancel")
            yield Button("Apply safe changes", id="apply-import", variant="success")
        yield Footer()

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.exit(None)

    @on(Button.Pressed, "#apply-import")
    def apply_import(self) -> None:
        resolutions: Dict[str, str] = {}
        for index, action in enumerate(self.plan.conflicts):
            resolution = self.query_one(f"#import-resolution-{index}", Select).value
            if resolution == "merge":
                resolutions[action.path] = self.query_one(
                    f"#import-merge-{index}", TextArea
                ).text
        self.exit(resolutions)


class ToolingConfigApp(FactoryApp[Optional[ToolPolicy]]):
    CSS = APP_CSS
    TITLE = "AI Software Factory - Tool Kit"

    def __init__(self, policy: ToolPolicy) -> None:
        super().__init__()
        self.policy = policy

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="questionnaire"):
            yield Static("AI tool kit", classes="section-title")
            yield Static(
                "Instructions is inactive by default. Guardrails adds project-local "
                "permissions and report-only validation hooks after review.",
                classes="section-help",
            )
            yield Label("Kit level", classes="field-label")
            yield Select(
                [
                    ("Instructions — canonical instructions only", "instructions"),
                    ("Guardrails — permissions and safety hooks", "guardrails"),
                    ("Automation — guardrails plus observed commands", "automation"),
                    ("Custom — owner-managed policy", "custom"),
                ],
                value=self.policy.level,
                allow_blank=False,
                id="tooling-level",
            )
            yield Label("Tool kit providers", classes="field-label")
            yield SelectionList[str](
                *[
                    (tool, tool, tool in self.policy.enabled_tools)
                    for tool in TOOL_IDS
                ],
                id="tooling-tools",
            )
            yield Label("Hooks", classes="field-label")
            yield SelectionList[str](
                (
                    "Protect factory-owned configuration",
                    "protect_factory_assets",
                    self.policy.protect_factory_assets,
                ),
                (
                    "Run report-only factory validation when the agent stops",
                    "validate_on_stop",
                    self.policy.validate_on_stop,
                ),
                id="tooling-hooks",
            )
            yield Label("Observed commands", classes="field-label")
            yield Static(
                "Select only commands that have run successfully in this repository. "
                "Expected commands never become automation hooks automatically.",
                classes="field-help",
            )
            if self.policy.commands:
                yield SelectionList[str](
                    *[
                        (
                            f"{name}: {command.command}",
                            name,
                            command.evidence == "Observed",
                        )
                        for name, command in self.policy.commands.items()
                    ],
                    id="tooling-observed-commands",
                )
            else:
                yield Static(
                    "No project commands are configured.",
                    id="tooling-observed-commands-empty",
                    classes="help",
                )
            yield Static("", id="tooling-error", classes="error")
        with Horizontal(id="actions"):
            yield Button("Cancel", id="cancel-tooling")
            yield Button("Review changes", id="review-tooling", variant="success")
        yield Footer()

    @on(Select.Changed, "#tooling-level")
    def level_changed(self, event: Select.Changed) -> None:
        if event.value == "instructions":
            hooks = self.query_one("#tooling-hooks", SelectionList)
            hooks.deselect_all()
        elif event.value in {"guardrails", "automation"}:
            hooks = self.query_one("#tooling-hooks", SelectionList)
            hooks.select("protect_factory_assets")
            hooks.select("validate_on_stop")

    @on(Button.Pressed, "#cancel-tooling")
    def cancel_tooling(self) -> None:
        self.exit(None)

    @on(Button.Pressed, "#review-tooling")
    def review_tooling(self) -> None:
        level = str(self.query_one("#tooling-level", Select).value)
        tools = list(self.query_one("#tooling-tools", SelectionList).selected)
        hooks = set(self.query_one("#tooling-hooks", SelectionList).selected)
        observed = (
            set(
                self.query_one(
                    "#tooling-observed-commands", SelectionList
                ).selected
            )
            if self.policy.commands
            else set()
        )
        if not tools:
            self.query_one("#tooling-error", Static).update(
                "Select at least one AI coding tool."
            )
            return
        policy = ToolPolicy(
            status="approved",
            level=level,
            enabled_tools=tools,
            protect_factory_assets="protect_factory_assets" in hooks,
            validate_on_stop="validate_on_stop" in hooks,
            commands={
                name: CommandPolicy(
                    command=command.command,
                    evidence="Observed" if name in observed else "Expected",
                )
                for name, command in self.policy.commands.items()
            },
        )
        try:
            policy.validate()
        except ValueError as exc:
            self.query_one("#tooling-error", Static).update(str(exc))
            return
        self.exit(policy)


class ToolingReviewApp(FactoryApp[Optional[Dict[str, Optional[str]]]]):
    CSS = APP_CSS
    TITLE = "AI Software Factory - Tooling Review"

    def __init__(self, plan: ImportPlan, markdown: str) -> None:
        super().__init__()
        self.plan = plan
        self.markdown = markdown

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="tooling-preview", id="import-tabs"):
            with TabPane("Preview", id="tooling-preview"):
                yield MarkdownViewer(
                    self.markdown,
                    show_table_of_contents=False,
                    id="tooling-preview-viewer",
                )
            with TabPane("Existing files", id="tooling-conflicts"):
                with VerticalScroll(classes="tab-scroll"):
                    if not self.plan.conflicts:
                        yield Static("No provider configuration conflicts.", classes="section")
                    for index, action in enumerate(self.plan.conflicts):
                        yield Label(action.path, classes="field-label")
                        yield Static(
                            (
                                "Skip keeps this previously managed file active. "
                                "Remove deactivates it after this review."
                                if action.proposed_content is None
                                else "Skip keeps the existing file and saves this proposal. "
                                "Replace publishes only the reviewed content below."
                            ),
                            classes="field-help",
                        )
                        yield Select(
                            (
                                [
                                    ("Skip and keep active", "skip"),
                                    ("Remove reviewed file", "remove"),
                                ]
                                if action.proposed_content is None
                                else [
                                    ("Skip and save proposal", "skip"),
                                    ("Publish reviewed content", "replace"),
                                ]
                            ),
                            value="skip",
                            allow_blank=False,
                            id=f"tooling-resolution-{index}",
                        )
                        if action.proposed_content is not None:
                            yield TextArea(
                                action.proposed_content,
                                id=f"tooling-content-{index}",
                            )
        with Horizontal(id="actions"):
            yield Button("Cancel", id="cancel-tooling-review")
            yield Button("Apply reviewed kit", id="apply-tooling", variant="success")
        yield Footer()

    @on(Button.Pressed, "#cancel-tooling-review")
    def cancel_review(self) -> None:
        self.exit(None)

    @on(Button.Pressed, "#apply-tooling")
    def apply_review(self) -> None:
        resolutions: Dict[str, Optional[str]] = {}
        for index, action in enumerate(self.plan.conflicts):
            resolution = self.query_one(
                f"#tooling-resolution-{index}", Select
            ).value
            if resolution == "replace":
                resolutions[action.path] = self.query_one(
                    f"#tooling-content-{index}", TextArea
                ).text
            elif resolution == "remove":
                resolutions[action.path] = None
        self.exit(resolutions)


class ScaffoldReviewApp(FactoryApp[Optional[Dict[str, ScaffoldOutput]]]):
    CSS = APP_CSS
    TITLE = "AI Software Factory - Scaffold Review"

    def __init__(
        self,
        plan: ScaffoldPublishPlan,
        markdown: str,
        *,
        noun: str = "scaffold",
    ) -> None:
        super().__init__()
        self.plan = plan
        self.markdown = markdown
        self.noun = noun
        if noun != "scaffold":
            self.title = f"AI Software Factory - {noun.title()} Review"

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent(initial="scaffold-preview", id="import-tabs"):
            with TabPane("Preview", id="scaffold-preview"):
                yield MarkdownViewer(
                    self.markdown,
                    show_table_of_contents=False,
                    id="scaffold-preview-viewer",
                )
            with TabPane("Conflicts", id="scaffold-conflicts"):
                with VerticalScroll(classes="tab-scroll"):
                    if not self.plan.conflicts:
                        yield Static(
                            f"No {self.noun} conflicts were detected.",
                            classes="section",
                        )
                    for index, action in enumerate(self.plan.conflicts):
                        output = action.output
                        yield Label(action.path, classes="field-label")
                        yield Static(
                            f"Skip preserves the existing {self.noun} and saves a proposal. "
                            "Publish replaces it only after this explicit review.",
                            classes="field-help",
                        )
                        yield Select(
                            [
                                ("Skip and save proposal", "skip"),
                                ("Publish reviewed output", "publish"),
                            ],
                            value="skip",
                            allow_blank=False,
                            id=f"scaffold-resolution-{index}",
                        )
                        if output is not None and output.is_text:
                            yield TextArea(
                                output.text or "",
                                id=f"scaffold-content-{index}",
                            )
                        elif output is not None:
                            yield Static(
                                f"Binary output: {len(output.content)} bytes; "
                                f"sha256 {sha256(output.content).hexdigest()}",
                                id=f"scaffold-binary-{index}",
                                classes="help",
                            )
        with Horizontal(id="actions", classes="two-actions"):
            yield Button("Cancel", id="cancel-scaffold-review")
            yield Button(
                f"Apply reviewed {self.noun}",
                id="apply-scaffold",
                variant="success",
            )
        yield Footer()

    @on(Button.Pressed, "#cancel-scaffold-review")
    def cancel_review(self) -> None:
        self.exit(None)

    @on(Button.Pressed, "#apply-scaffold")
    def apply_review(self) -> None:
        resolutions: Dict[str, ScaffoldOutput] = {}
        for index, action in enumerate(self.plan.conflicts):
            resolution = self.query_one(
                f"#scaffold-resolution-{index}", Select
            ).value
            output = action.output
            if resolution != "publish" or output is None:
                continue
            if output.is_text:
                content = self.query_one(
                    f"#scaffold-content-{index}", TextArea
                ).text.encode("utf-8")
                output = ScaffoldOutput(
                    path=output.path,
                    content=content,
                    adapter_id=output.adapter_id,
                    executable=output.executable,
                )
            resolutions[action.path] = output
        self.exit(resolutions)


RefinementOutcome = Tuple[str, Optional[str]]
RefinementOperation = Callable[
    [Callable[[str], None], Event],
    RefinementOutcome,
]


class RefinementApp(FactoryApp[Optional[RefinementOutcome]]):
    CSS = APP_CSS
    TITLE = "AI Software Factory - Refining Specs"

    def __init__(self, tool_id: str, operation: RefinementOperation) -> None:
        super().__init__()
        self.tool_id = tool_id
        self.operation = operation
        self.cancel_event = Event()
        self.started_at = monotonic()
        self.finished = False

    def compose(self) -> ComposeResult:
        yield Header()
        with Vertical(id="refinement-body"):
            with Vertical(id="refinement-card"):
                yield Static(
                    f"Refining project specs with {self.tool_id}",
                    id="refinement-title",
                )
                yield LoadingIndicator(id="refinement-spinner")
                yield Static("Preparing deterministic draft…", id="refinement-status")
                yield Static("Elapsed: 00:00", id="refinement-elapsed")
                yield Static(
                    "Running in an isolated, read-only staging directory.",
                    id="refinement-safety",
                )
        with Horizontal(id="actions"):
            yield Button("Cancel refinement", id="cancel-refinement")
        yield Footer()

    def on_mount(self) -> None:
        self.started_at = monotonic()
        self.set_interval(1.0, self.update_elapsed)
        self.run_worker(
            self.run_refinement,
            thread=True,
            exit_on_error=False,
            exclusive=True,
        )

    def on_unmount(self) -> None:
        if not self.finished:
            self.cancel_event.set()

    def run_refinement(self) -> None:
        try:
            result = self.operation(self.report_progress, self.cancel_event)
        except Exception as exc:  # pragma: no cover - defensive UI boundary
            self.call_from_thread(self.finish_with_error, str(exc))
            return
        self.call_from_thread(self.finish_refinement, result)

    def report_progress(self, message: str) -> None:
        if self.is_running:
            self.call_from_thread(self.set_status, message)

    def set_status(self, message: str) -> None:
        self.query_one("#refinement-status", Static).update(message)

    def update_elapsed(self) -> None:
        elapsed = max(0, int(monotonic() - self.started_at))
        minutes, seconds = divmod(elapsed, 60)
        self.query_one("#refinement-elapsed", Static).update(
            f"Elapsed: {minutes:02d}:{seconds:02d}"
        )

    def finish_refinement(self, result: RefinementOutcome) -> None:
        self.finished = True
        if self.cancel_event.is_set():
            self.exit(None)
            return
        self.exit(result)

    def finish_with_error(self, message: str) -> None:
        self.finished = True
        if self.cancel_event.is_set():
            self.exit(None)
            return
        self.query_one("#refinement-spinner", LoadingIndicator).display = False
        self.set_status(f"Refinement failed: {message}")
        self.query_one("#cancel-refinement", Button).label = "Close"

    @on(Button.Pressed, "#cancel-refinement")
    def cancel_refinement(self) -> None:
        if self.finished:
            self.exit(None)
            return
        self.cancel_event.set()
        self.set_status("Cancelling refinement…")
        self.query_one("#cancel-refinement", Button).disabled = True


class ClarificationApp(FactoryApp[str]):
    CSS = APP_CSS
    TITLE = "AI Software Factory - Clarification"

    def __init__(self, clarification: Clarification) -> None:
        super().__init__()
        self.clarification = clarification
        self.question_widgets: Dict[str, Tuple[str, str]] = {}
        self.pending_answers: Optional[Dict[str, Any]] = None

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="questionnaire"):
            yield Static(
                f"{self.clarification.clarification_id} · {self.clarification.task_id}",
                classes="section",
            )
            yield Static("", id="progress", classes="help")
            for index, question in enumerate(self.clarification.questions):
                container_id = f"question-{index}"
                widget_id = f"answer-{index}"
                self.question_widgets[question.question_id] = (widget_id, container_id)
                with Vertical(id=container_id, classes="section"):
                    required = " *" if question.required else ""
                    yield Label(f"{index + 1}. {question.prompt}{required}", classes="field-label")
                    if question.context:
                        yield Static(question.context, classes="help")
                    if question.recommendation:
                        yield Static(f"Recommendation: {question.recommendation}", classes="help")
                    answer = self.clarification.answers.get(question.question_id)
                    if question.question_type == "free_text":
                        yield TextArea(str(answer or ""), id=widget_id)
                    elif question.question_type in {"confirmation", "single_choice"}:
                        options = question.options
                        if question.question_type == "confirmation" and not options:
                            options = [
                                {"label": "Yes", "value": "yes"},
                                {"label": "No", "value": "no"},
                            ]
                        yield Select(
                            [
                                (str(option.get("label", option.get("value", ""))), str(option.get("value", "")))
                                for option in options
                            ],
                            value=str(answer) if answer not in (None, "") else Select.NULL,
                            allow_blank=True,
                            id=widget_id,
                        )
                    else:
                        selected = set(answer or [])
                        yield SelectionList[str](
                            *[
                                (
                                    str(option.get("label", option.get("value", ""))),
                                    str(option.get("value", "")),
                                    str(option.get("value", "")) in selected,
                                )
                                for option in question.options
                            ],
                            id=widget_id,
                        )
            yield Static("", id="error", classes="error")
        with Horizontal(id="actions"):
            yield Button("Cancel", id="cancel")
            yield Button("Save and exit", id="save")
            yield Button("Submit", id="submit", variant="success")
        yield Footer()

    def on_mount(self) -> None:
        self.update_dependencies()

    def collect_answers(self) -> Dict[str, Any]:
        answers: Dict[str, Any] = {}
        for question in self.clarification.questions:
            widget_id, _ = self.question_widgets[question.question_id]
            if question.question_type == "free_text":
                value: Any = self.query_one(f"#{widget_id}", TextArea).text.strip()
            elif question.question_type in {"confirmation", "single_choice"}:
                selected = self.query_one(f"#{widget_id}", Select).value
                value = "" if selected is Select.NULL else str(selected)
            else:
                value = list(self.query_one(f"#{widget_id}", SelectionList).selected)
            answers[question.question_id] = value
        return answers

    def update_dependencies(self) -> None:
        answers = self.collect_answers()
        active = []
        for question in self.clarification.questions:
            _, container_id = self.question_widgets[question.question_id]
            is_active = self.clarification.is_active(question, answers)
            self.query_one(f"#{container_id}", Vertical).display = is_active
            if is_active:
                active.append(question)
        answered = sum(
            answers.get(question.question_id) not in (None, "", []) for question in active
        )
        self.query_one("#progress", Static).update(
            f"Progress: {answered}/{len(active)} active questions answered"
        )

    @on(Select.Changed)
    def select_changed(self) -> None:
        self.update_dependencies()

    @on(SelectionList.SelectedChanged)
    def selection_changed(self) -> None:
        self.update_dependencies()

    @on(TextArea.Changed)
    def text_changed(self) -> None:
        self.update_dependencies()

    @on(Button.Pressed, "#cancel")
    def cancel(self) -> None:
        self.exit("cancelled")

    @on(Button.Pressed, "#save")
    def save(self) -> None:
        save_clarification(self.clarification, self.collect_answers(), submit=False)
        self.exit("saved")

    @on(Button.Pressed, "#submit")
    def submit(self) -> None:
        answers = self.collect_answers()
        missing = self.clarification.missing_required(answers)
        if missing:
            self.query_one("#error", Static).update(
                f"Required questions are unanswered: {', '.join(missing)}"
            )
            return
        self.pending_answers = answers
        self.exit("review")


def _format_age(created_at: str) -> str:
    """Render an ISO timestamp as a short age like '2h' or '35m'."""
    from datetime import datetime, timezone

    try:
        started = datetime.fromisoformat(created_at)
    except (ValueError, TypeError):
        return ""
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    seconds = (datetime.now(timezone.utc) - started).total_seconds()
    if seconds < 0:
        return ""
    if seconds < 3600:
        return f"{int(seconds // 60)}m"
    if seconds < 86400:
        return f"{int(seconds // 3600)}h"
    return f"{int(seconds // 86400)}d"


class TaskCard(Button):
    """A focusable task chip that remembers its task id and column state."""

    def __init__(
        self,
        task_id: str,
        title: str,
        state: str,
        annotation: str = "",
        moved: bool = False,
    ) -> None:
        label = f"{task_id} · {title}" if title else task_id
        if annotation:
            label = f"{label}  [{annotation}]"
        if moved:
            label = f"• {label}"
        super().__init__(label, classes="task-card moved" if moved else "task-card")
        self.task_id = task_id
        self.state = state


class TaskDetailScreen(ModalScreen[None]):
    """Read-only overlay showing the full Markdown body of one task."""

    CSS = APP_CSS
    BINDINGS = [("escape,q,enter", "dismiss", "Close")]

    def __init__(self, heading: str, body: str) -> None:
        super().__init__()
        self.heading = heading
        self.body = body or "_This task has no stored content._"

    def compose(self) -> ComposeResult:
        with Vertical(id="task-detail"):
            yield Static(self.heading, classes="board-column-title")
            yield MarkdownViewer(
                self.body, show_table_of_contents=False, id="task-detail-body"
            )
            yield Footer()


class BoardApp(FactoryApp[None]):
    """Kanban board over the lifecycle task states for one project.

    Moves are *staged*: arrow keys reposition a card in memory only. Press
    ``s`` to persist all pending moves, ``c`` to discard them, or ``u`` to undo
    one step. Press Enter on a card to view its full detail.
    """

    CSS = APP_CSS
    TITLE = "AI Software Factory - Board"
    BINDINGS = [
        ("left,h", "move(-1)", "Move left"),
        ("right,l", "move(1)", "Move right"),
        ("d", "view", "View"),
        ("s", "save", "Save"),
        ("c", "cancel", "Discard"),
        ("u", "undo", "Undo"),
        ("r", "reload", "Refresh"),
        ("q", "quit_guarded", "Quit"),
    ]

    def __init__(
        self,
        store: Any,
        project_name: str,
        read_only: bool = False,
        assignments: Optional[Dict[str, Tuple[str, str]]] = None,
    ) -> None:
        super().__init__()
        self.store = store
        self.project_name = project_name
        self.read_only = read_only
        self.sub_title = project_name
        self.tasks: List[Any] = list(store.list_tasks())
        # task_id -> (tool_id, created_at) for tasks an agent is dispatched on.
        self.assignments: Dict[str, Tuple[str, str]] = assignments or {}
        # Staged, not-yet-saved moves: task_id -> target state.
        self.pending: Dict[str, str] = {}
        # Undo history: (task_id, state before the move) in chronological order.
        self.undo_stack: List[Tuple[str, str]] = []
        self._pending_focus: Optional[str] = None
        self._quit_armed = False

    # -- state helpers -------------------------------------------------------

    def _annotation(self, task) -> str:
        assignment = self.assignments.get(task.task_id)
        if assignment:
            tool_id, created_at = assignment
            age = _format_age(created_at)
            return f"{tool_id} · {age}" if age else tool_id
        owner = getattr(task, "owner", None)
        return f"@{owner}" if owner else ""

    def _committed_state(self, task_id: str) -> Optional[str]:
        for task in self.tasks:
            if task.task_id == task_id:
                return task.state
        return None

    def _current_state(self, task_id: str) -> Optional[str]:
        return self.pending.get(task_id, self._committed_state(task_id))

    def _status_text(self) -> str:
        if self.read_only:
            return "Read-only board."
        count = len(self.pending)
        if count:
            return (
                f"● {count} unsaved change(s) — s Save · c Discard · u Undo · "
                "Enter to view"
            )
        return "←/→ move · Enter view · s Save · c Discard · u Undo · q Quit"

    # -- layout --------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="board"):
            for state in TASK_STATES:
                column = [
                    task for task in self.tasks if self._current_state(task.task_id) == state
                ]
                with Vertical(classes="board-column"):
                    yield Static(
                        f"{state.upper()} ({len(column)})",
                        classes="board-column-title",
                    )
                    with VerticalScroll(classes="board-column-body"):
                        if not column:
                            yield Static("—", classes="board-empty")
                        for task in column:
                            card = TaskCard(
                                task.task_id,
                                task.title,
                                state,
                                annotation=self._annotation(task),
                                moved=task.task_id in self.pending,
                            )
                            card.disabled = self.read_only
                            yield card
        status = Static(self._status_text(), id="board-status")
        if self.pending:
            status.add_class("dirty")
        yield status
        yield Footer()

    # -- actions -------------------------------------------------------------

    async def action_move(self, delta: int) -> None:
        if self.read_only:
            self.notify("Board is read-only.", severity="warning")
            return
        card = self.focused
        if not isinstance(card, TaskCard):
            self.notify("Select a task, then press ←/→ to move it.")
            return
        self._quit_armed = False
        current = self._current_state(card.task_id)
        index = TASK_STATES.index(current)
        target = index + delta
        if not 0 <= target < len(TASK_STATES):
            self.bell()
            return
        self.undo_stack.append((card.task_id, current))
        self._set_pending(card.task_id, TASK_STATES[target])
        self._pending_focus = card.task_id
        await self._refresh()

    def _set_pending(self, task_id: str, state: str) -> None:
        if state == self._committed_state(task_id):
            self.pending.pop(task_id, None)
        else:
            self.pending[task_id] = state

    async def action_undo(self) -> None:
        self._quit_armed = False
        if not self.undo_stack:
            self.notify("Nothing to undo.")
            return
        task_id, previous = self.undo_stack.pop()
        self._set_pending(task_id, previous)
        self._pending_focus = task_id
        await self._refresh()

    async def action_save(self) -> None:
        self._quit_armed = False
        if not self.pending:
            self.notify("No changes to save.")
            return
        errors: List[str] = []
        conflicts: List[str] = []
        saved = 0
        for task_id, target in list(self.pending.items()):
            try:
                fresh = self.store.get_task(task_id)
            except Exception as exc:  # surfaced to the user, not the traceback
                errors.append(f"{task_id}: {exc}")
                continue
            if fresh is None:
                conflicts.append(f"{task_id} no longer exists")
                continue
            if fresh.state == target:
                saved += 1  # already where we wanted it
                continue
            # Someone else moved this task since the board was loaded.
            if fresh.state != self._committed_state(task_id):
                conflicts.append(f"{task_id} changed to {fresh.state} elsewhere")
                continue
            try:
                self.store.move_task(task_id, target)
                saved += 1
            except Exception as exc:
                errors.append(f"{task_id}: {exc}")
        self.tasks = list(self.store.list_tasks())
        self.pending.clear()
        self.undo_stack.clear()
        await self._refresh(focus=False)
        problems = errors + conflicts
        if problems:
            self.notify(
                f"Saved {saved}; skipped: " + "; ".join(problems), severity="warning"
            )
        else:
            self.notify(f"Saved {saved} change(s).")

    async def action_cancel(self) -> None:
        self._quit_armed = False
        if not self.pending:
            self.notify("Nothing to discard.")
            return
        self.pending.clear()
        self.undo_stack.clear()
        await self._refresh(focus=False)
        self.notify("Discarded unsaved changes.")

    def action_view(self) -> None:
        card = self.focused
        if not isinstance(card, TaskCard):
            return
        self._open_detail(card.task_id)

    @on(Button.Pressed)
    def _card_pressed(self, event: Button.Pressed) -> None:
        if isinstance(event.button, TaskCard):
            self._open_detail(event.button.task_id)

    def _open_detail(self, task_id: str) -> None:
        task = next((item for item in self.tasks if item.task_id == task_id), None)
        if task is None:
            return
        heading = f"{task.task_id} · {task.title}" if task.title else task.task_id
        # The list view loads no body (for speed); fetch it lazily on open.
        body = getattr(task, "body", None)
        if not body:
            try:
                full = self.store.get_task(task_id)
            except Exception:
                full = None
            if full is not None:
                body = full.body
        self.push_screen(TaskDetailScreen(heading, body or ""))

    def action_quit_guarded(self) -> None:
        if self.read_only or not self.pending:
            self.exit(None)
            return
        if self._quit_armed:
            self.exit(None)
            return
        self._quit_armed = True
        self.notify(
            "Unsaved changes. Press s to save, c to discard, or q again to quit "
            "without saving.",
            severity="warning",
        )

    async def action_reload(self) -> None:
        self._quit_armed = False
        self.tasks = list(self.store.list_tasks())
        self.pending.clear()
        self.undo_stack.clear()
        await self._refresh(focus=False)

    async def _refresh(self, focus: bool = True) -> None:
        await self.recompose()
        if focus:
            self.call_after_refresh(self._restore_focus)

    def _restore_focus(self) -> None:
        if not self._pending_focus:
            return
        for card in self.query(TaskCard):
            if card.task_id == self._pending_focus:
                card.focus()
                break
        self._pending_focus = None


class ProjectsApp(FactoryApp[Optional[Tuple[str, str]]]):
    """Pick a registered project; returns (project name, "board"|"dashboard")."""

    CSS = APP_CSS
    TITLE = "AI Software Factory - Projects"
    BINDINGS = [("q", "cancel", "Quit")]

    def __init__(self, entries: List[Any]) -> None:
        super().__init__()
        self.entries = entries

    def compose(self) -> ComposeResult:
        yield Header()
        if not self.entries:
            yield Static(
                "No projects registered. Run `factory init` or "
                "`factory projects add <path>`.",
                id="projects-list",
            )
        else:
            items = [
                ListItem(Label(f"{entry.name}  —  {entry.path}"))
                for entry in self.entries
            ]
            yield ListView(*items, id="projects-list")
        with Horizontal(id="actions", classes="three-actions"):
            yield Button("Cancel", id="cancel")
            yield Button("Open board", id="open-board", variant="success")
            yield Button("Open dashboard", id="open-dashboard", variant="primary")
        yield Footer()

    def _selected_name(self) -> Optional[str]:
        try:
            view = self.query_one("#projects-list", ListView)
        except Exception:
            return None
        index = view.index
        if index is None or not 0 <= index < len(self.entries):
            return None
        return self.entries[index].name

    def _open(self, action: str) -> None:
        name = self._selected_name()
        if name is None:
            self.notify("Select a project first.")
            return
        self.exit((name, action))

    @on(ListView.Selected)
    def _on_selected(self) -> None:
        self._open("board")

    @on(Button.Pressed, "#open-board")
    def _open_board(self) -> None:
        self._open("board")

    @on(Button.Pressed, "#open-dashboard")
    def _open_dashboard(self) -> None:
        self._open("dashboard")

    @on(Button.Pressed, "#cancel")
    def action_cancel(self) -> None:
        self.exit(None)


try:  # optional plotting backend; falls back to Unicode bars when absent
    from textual_plotext import PlotextPlot

    class DashboardChart(PlotextPlot):
        """A single plotext chart rendered from a metrics Chart spec."""

        def __init__(self, chart: Any) -> None:
            super().__init__(classes="dash-chart")
            self._chart = chart

        def on_mount(self) -> None:
            chart = self._chart
            plt = self.plt
            plt.clear_figure()
            if not chart.labels:
                plt.title(chart.title)
                return
            if chart.kind == "multi":
                plt.multiple_bar(
                    chart.labels, chart.series, labels=list(chart.series_names)
                )
            elif chart.kind == "hbar":
                plt.bar(chart.labels, chart.series[0], orientation="horizontal")
            else:
                plt.bar(chart.labels, chart.series[0])
            plt.title(chart.title)

except Exception:  # pragma: no cover - exercised only when the extra is absent
    PlotextPlot = None
    DashboardChart = None


class DashboardApp(FactoryApp[None]):
    """Read-only metrics dashboard: KPI cards, comparison charts, and tables."""

    CSS = APP_CSS
    TITLE = "AI Software Factory - Dashboard"
    BINDINGS = [
        ("r", "refresh", "Refresh"),
        ("t", "toggle_granularity", "Day/Week/Month"),
        ("q", "quit", "Quit"),
    ]

    def __init__(
        self,
        view_provider: Any,
        project_name: str,
    ) -> None:
        super().__init__()
        # Accept either a callable provider (so `r`/`t` can re-query) or a static
        # DashboardView/value (convenient for tests).
        if callable(view_provider):
            self._provider = view_provider
        else:
            snapshot = view_provider
            self._provider = lambda _granularity: snapshot
        self.project_name = project_name
        self.sub_title = project_name
        self.granularity = "day"
        self.view = self._provider(self.granularity)

    @property
    def summary(self):
        return getattr(self.view, "summary", [])

    @property
    def charts(self):
        return getattr(self.view, "charts", [])

    @property
    def tables(self):
        return getattr(self.view, "tables", self.view)

    def compose(self) -> ComposeResult:
        yield Header()
        with VerticalScroll(id="dashboard"):
            if not (self.summary or self.charts or self.tables):
                yield Static("No usage recorded yet.", classes="board-empty")
            if self.summary:
                with Horizontal(id="kpi-row"):
                    for kpi in self.summary:
                        with Vertical(classes="kpi alert" if kpi.alert else "kpi"):
                            yield Static(kpi.label, classes="kpi-label")
                            yield Static(kpi.value, classes="kpi-value")
                            if kpi.delta:
                                yield Static(kpi.delta, classes="kpi-delta")
            for chart in self.charts:
                if DashboardChart is not None and chart.labels:
                    yield DashboardChart(chart)
                else:
                    yield Static(chart.title, classes="dashboard-title")
                    yield Static(self._chart_text(chart), classes="chart")
            for title, columns, rows in self.tables:
                yield Static(title, classes="dashboard-title")
                yield self._build_table(columns, rows)
        yield Footer()

    @staticmethod
    def _chart_text(chart) -> str:
        from .metrics import render_chart_text

        return render_chart_text(chart)

    @staticmethod
    def _build_table(columns, rows) -> DataTable:
        from rich.text import Text

        status_idx = columns.index("Status") if "Status" in columns else -1
        remaining_idx = columns.index("Remaining") if "Remaining" in columns else -1
        table: DataTable = DataTable(zebra_stripes=True)
        table.add_columns(*columns)
        for row in rows:
            is_total = bool(row) and row[0] == "TOTAL"
            cells = []
            for index, value in enumerate(row):
                over = index == status_idx and value == "OVER"
                negative = index == remaining_idx and value.startswith("-")
                if over or negative:
                    cells.append(Text(value, style="bold red"))
                elif is_total:
                    cells.append(Text(value, style="bold"))
                else:
                    cells.append(value)
            table.add_row(*cells)
        return table

    async def action_refresh(self) -> None:
        self.view = self._provider(self.granularity)
        await self.recompose()
        self.notify("Refreshed.")

    async def action_toggle_granularity(self) -> None:
        order = ("day", "week", "month")
        self.granularity = order[(order.index(self.granularity) + 1) % len(order)]
        self.view = self._provider(self.granularity)
        await self.recompose()
        self.notify(f"Trend granularity: {self.granularity}")
