from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Tuple

from .models import ProjectIntake, TechChoice


@dataclass(frozen=True)
class CompatibilityInsight:
    level: str
    title: str
    message: str
    recommendation: str = ""
    questions: Tuple[str, ...] = ()


PROJECT_PRESETS: Dict[str, Dict[str, object]] = {
    "web-app": {
        "label": "Web App",
        "description": "Browser product with a full-stack web baseline.",
        "tech_stack": {
            "frontend": "Next.js",
            "database": "PostgreSQL",
            "ci_cd": "GitHub Actions",
            "deployment": "Managed platform deployment",
            "testing": "Vitest + Playwright",
        },
        "commands": {
            "install": "npm ci",
            "run": "npm run dev",
            "test": "npm test",
            "build": "npm run build",
            "lint": "npm run lint",
            "typecheck": "npm run typecheck",
            "format": "npm run format",
        },
    },
    "api": {
        "label": "API Service",
        "description": "HTTP API with a Python service and relational database baseline.",
        "tech_stack": {
            "backend": "Python + FastAPI + REST",
            "database": "PostgreSQL",
            "ci_cd": "GitHub Actions",
            "testing": "pytest + Playwright",
        },
        "commands": {
            "install": "pip install -e .",
            "run": "uvicorn app.main:app --reload",
            "test": "pytest",
            "build": "python -m build",
            "lint": "ruff check .",
            "typecheck": "mypy .",
            "format": "ruff format .",
            "migration": "alembic upgrade head",
        },
    },
    "cli": {
        "label": "CLI",
        "description": "Python command-line application baseline.",
        "tech_stack": {
            "backend": "Python CLI",
            "database": "Not applicable",
            "testing": "pytest",
        },
        "commands": {
            "install": "pip install -e .",
            "run": "python -m app",
            "test": "pytest",
            "build": "python -m build",
            "lint": "ruff check .",
            "typecheck": "mypy .",
            "format": "ruff format .",
        },
    },
    "mobile": {
        "label": "Mobile App",
        "description": "Cross-platform Flutter mobile application baseline.",
        "tech_stack": {
            "mobile": "Flutter",
            "testing": "Flutter test",
        },
        "commands": {
            "install": "flutter pub get",
            "run": "flutter run",
            "test": "flutter test",
            "build": "flutter build",
            "lint": "flutter analyze",
            "format": "dart format --output=none --set-exit-if-changed lib test",
        },
    },
}


REFINEMENT_SECTIONS: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "all": ("Entire specification", ()),
    "overview": (
        "Overview, vision, and users",
        ("Summary", "Vision", "Users And Stakeholders"),
    ),
    "scope": (
        "Scope, roadmap, flows, and features",
        ("Scope", "Roadmap", "Core User Flows", "Features"),
    ),
    "experience": (
        "UX and data model",
        ("UX/UI Direction", "Data And Domain Model"),
    ),
    "technical": ("Technical direction", ("Technical Direction",)),
    "quality": (
        "Quality, delivery, and operations",
        ("Quality Attributes", "Delivery And Operations"),
    ),
    "risk-validation": (
        "Risks, validation, and work breakdown",
        (
            "Risks And Assumptions",
            "Validation Strategy",
            "Initial Work Breakdown",
            "Decision And Confidence Summary",
        ),
    ),
}


def apply_project_preset(intake: ProjectIntake, preset_id: str) -> ProjectIntake:
    """Fill only blank values so a preset never overwrites owner input."""
    preset = PROJECT_PRESETS.get(preset_id)
    if preset is None:
        return intake
    intake.project_preset = preset_id
    for area, value in dict(preset["tech_stack"]).items():
        choice = intake.tech_stack.get(area)
        if choice is not None and not choice.value.strip():
            intake.tech_stack[area] = TechChoice(str(value), "Proposed")
    for name, value in dict(preset["commands"]).items():
        if name in intake.commands and not intake.commands[name].strip():
            intake.commands[name] = str(value)
    return intake


def _stack_value(stack: Mapping[str, TechChoice], area: str) -> str:
    choice = stack.get(area)
    return choice.value.strip().lower() if choice else ""


def analyze_compatibility(intake: ProjectIntake) -> List[CompatibilityInsight]:
    stack = intake.tech_stack
    frontend = _stack_value(stack, "frontend")
    mobile = _stack_value(stack, "mobile")
    backend = _stack_value(stack, "backend")
    database = _stack_value(stack, "database")
    infrastructure = _stack_value(stack, "infrastructure")
    deployment = _stack_value(stack, "deployment")
    testing = _stack_value(stack, "testing")
    insights: List[CompatibilityInsight] = []

    if "next.js" in frontend and "django" in backend:
        insights.append(
            CompatibilityInsight(
                "info",
                "Split-stack architecture inferred",
                "Next.js is likely the web frontend while Django exposes a separate backend API.",
                "Define the API style and service boundary before implementation.",
                ("Who owns authentication?", "How are both services deployed?"),
            )
        )
    elif "next.js" in frontend and not backend:
        insights.append(
            CompatibilityInsight(
                "info",
                "Backend ownership is open",
                "Next.js can own server-side behavior, but no backend direction is recorded.",
                "Confirm whether this is a single Next.js application or needs a separate API.",
            )
        )
    elif frontend and backend:
        insights.append(
            CompatibilityInsight(
                "info",
                "Frontend/API boundary inferred",
                "Separate frontend and backend technologies imply at least two runtime boundaries.",
                "Record API style, authentication ownership, and local development orchestration.",
            )
        )

    if "sqlite" in database and any(
        marker in f"{infrastructure} {deployment}"
        for marker in ("container", "kubernetes", "ecs", "cloud")
    ):
        insights.append(
            CompatibilityInsight(
                "warning",
                "SQLite scaling constraint",
                "A local SQLite file may conflict with multiple containers or "
                "horizontally scaled deployments.",
                "Use a managed relational database or explicitly constrain the service "
                "to one writable instance.",
            )
        )

    if "mongodb" in database and "django" in backend:
        insights.append(
            CompatibilityInsight(
                "warning",
                "Django MongoDB compatibility must be reviewed",
                "The official MongoDB backend does not support every Django field, "
                "migration operation, or management command.",
                "Review the backend compatibility matrix before approving this combination.",
            )
        )

    if "manual deployment" in deployment and infrastructure and "managed" not in infrastructure:
        insights.append(
            CompatibilityInsight(
                "warning",
                "Manual delivery risk",
                "Provisioned infrastructure with manual deployment can make releases "
                "difficult to reproduce.",
                "Define an automated delivery path or document the accepted operational tradeoff.",
            )
        )

    if "pytest" in testing and backend and not any(
        marker in backend for marker in ("python", "django", "fastapi", "flask")
    ):
        insights.append(
            CompatibilityInsight(
                "warning",
                "Test runner may not cover the backend",
                "pytest is selected but the backend does not appear to be Python-based.",
                "Confirm whether pytest covers another component or choose a "
                "backend-native runner.",
            )
        )

    if mobile == "not applicable" and "mobile" in (
        f"{intake.goals} {intake.mvp_scope} {intake.core_flows}".lower()
    ):
        insights.append(
            CompatibilityInsight(
                "warning",
                "Mobile scope needs confirmation",
                "The scope mentions mobile behavior while the mobile technology is "
                "marked Not applicable.",
                "Clarify whether responsive web is sufficient or a mobile application is required.",
            )
        )
    return insights


def command_suggestions(
    stack: Mapping[str, TechChoice],
) -> Dict[str, Tuple[str, ...]]:
    values = " ".join(choice.value.lower() for choice in stack.values())
    suggestions: Dict[str, List[str]] = {
        "install": [],
        "run": [],
        "test": [],
        "build": [],
        "lint": [],
        "typecheck": [],
        "format": [],
        "migration": [],
    }

    def add(name: str, *commands: str) -> None:
        for command in commands:
            if command not in suggestions[name]:
                suggestions[name].append(command)

    if any(
        marker in values
        for marker in (
            "next.js",
            "react",
            "vue",
            "svelte",
            "angular",
            "node.js",
            "nestjs",
        )
    ):
        add("install", "npm ci", "pnpm install --frozen-lockfile")
        add("run", "npm run dev")
        add("test", "npm test")
        add("build", "npm run build")
        add("lint", "npm run lint")
        add("typecheck", "npm run typecheck")
        add("format", "npm run format")
        add("migration", "npm run migrate")
    if any(marker in values for marker in ("python", "django", "fastapi", "pytest")):
        add("install", "pip install -e .")
        add("run", "uvicorn app.main:app --reload", "python manage.py runserver")
        add("test", "pytest")
        add("build", "python -m build")
        add("lint", "ruff check .")
        add("typecheck", "mypy .", "pyright")
        add("format", "ruff format .")
        add("migration", "alembic upgrade head", "python manage.py migrate")
    if "flutter" in values:
        add("install", "flutter pub get")
        add("run", "flutter run")
        add("test", "flutter test")
        add("build", "flutter build")
        add("lint", "flutter analyze")
        add("format", "dart format --output=none --set-exit-if-changed lib test")
    if "spring boot" in values:
        add("install", "./mvnw dependency:go-offline")
        add("run", "./mvnw spring-boot:run")
        add("test", "./mvnw test")
        add("build", "./mvnw verify")
    if "asp.net core" in values:
        add("install", "dotnet restore")
        add("run", "dotnet run")
        add("test", "dotnet test")
        add("build", "dotnet build --no-restore")
        add("format", "dotnet format")
    if "go +" in values:
        add("install", "go mod download")
        add("run", "go run .")
        add("test", "go test ./...")
        add("build", "go build ./...")
        add("lint", "go vet ./...")
        add("format", "gofmt -w .")
    for name in suggestions:
        add(name, f"make {name}")
    return {name: tuple(values) for name, values in suggestions.items()}


def refinement_headings(section_ids: List[str]) -> Tuple[str, ...]:
    if "all" in section_ids:
        return ()
    headings: List[str] = []
    for section_id in section_ids:
        for heading in REFINEMENT_SECTIONS.get(section_id, ("", ()))[1]:
            if heading not in headings:
                headings.append(heading)
    return tuple(headings)
