from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional

import yaml

from .constants import (
    PROJECT_PRESET_IDS,
    REFINEMENT_SECTION_IDS,
    STACK_STATUSES,
    TOOL_KIT_LEVELS,
    TOOL_IDS,
)


@dataclass
class TechChoice:
    value: str = ""
    status: str = "Unknown"

    def validate(self) -> None:
        if not isinstance(self.value, str) or not isinstance(self.status, str):
            raise ValueError("Technology choice value and status must be strings.")
        if self.status not in STACK_STATUSES:
            raise ValueError(f"Invalid technology status: {self.status}")


def default_tech_stack() -> Dict[str, TechChoice]:
    return {
        area: TechChoice()
        for area in (
            "frontend",
            "mobile",
            "backend",
            "database",
            "infrastructure",
            "ci_cd",
            "deployment",
            "testing",
        )
    }


def default_commands() -> Dict[str, str]:
    return {
        name: ""
        for name in (
            "install",
            "run",
            "test",
            "build",
            "lint",
            "typecheck",
            "format",
            "migration",
        )
    }


@dataclass
class ProjectIntake:
    project_name: str
    project_preset: str = ""
    one_line_description: str = ""
    problem_statement: str = ""
    intended_outcome: str = ""
    primary_users: str = ""
    goals: str = ""
    non_goals: str = ""
    mvp_scope: str = ""
    post_mvp_scope: str = ""
    out_of_scope: str = ""
    core_flows: str = ""
    constraints: str = ""
    integrations: str = ""
    raw_draft: str = ""
    tools: List[str] = field(default_factory=lambda: list(TOOL_IDS))
    refiner: Optional[str] = None
    use_ai: bool = False
    refinement_sections: List[str] = field(default_factory=lambda: ["all"])
    refinement_timeout_seconds: int = 300
    tool_kit_level: str = "instructions"
    tech_stack: Dict[str, TechChoice] = field(default_factory=default_tech_stack)
    commands: Dict[str, str] = field(default_factory=default_commands)
    refinement: Dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if not isinstance(self.project_name, str) or not self.project_name.strip():
            raise ValueError("Project name is required.")
        if not isinstance(self.tools, list) or not all(
            isinstance(tool, str) for tool in self.tools
        ):
            raise ValueError("Enabled AI tools must be a list of tool IDs.")
        if self.refiner is not None and not isinstance(self.refiner, str):
            raise ValueError("Default refiner must be a tool ID or null.")
        invalid_tools = sorted(set(self.tools) - set(TOOL_IDS))
        if invalid_tools:
            raise ValueError(f"Unsupported AI tools: {', '.join(invalid_tools)}")
        if self.refiner and self.refiner not in self.tools:
            raise ValueError("Default refiner must be one of the enabled tools.")
        if self.use_ai and not self.refiner:
            raise ValueError("AI refinement requires a default refiner.")
        if not isinstance(self.use_ai, bool):
            raise ValueError("AI refinement flag must be a boolean.")
        if not isinstance(self.project_preset, str):
            raise ValueError("Project preset must be a string.")
        if self.project_preset and self.project_preset not in PROJECT_PRESET_IDS:
            raise ValueError(f"Unsupported project preset: {self.project_preset}")
        if not isinstance(self.refinement_sections, list) or not all(
            isinstance(section, str) for section in self.refinement_sections
        ):
            raise ValueError("Refinement sections must be a list of section IDs.")
        invalid_sections = sorted(
            set(self.refinement_sections) - set(REFINEMENT_SECTION_IDS)
        )
        if invalid_sections:
            raise ValueError(
                f"Unsupported refinement sections: {', '.join(invalid_sections)}"
            )
        if self.use_ai and not self.refinement_sections:
            raise ValueError("AI refinement requires at least one target section.")
        if type(self.refinement_timeout_seconds) is not int:
            raise ValueError("Refinement timeout must be an integer.")
        if self.refinement_timeout_seconds < 1:
            raise ValueError("Refinement timeout must be positive.")
        if self.tool_kit_level not in TOOL_KIT_LEVELS:
            raise ValueError(f"Unsupported tool kit level: {self.tool_kit_level}")
        text_fields = (
            "one_line_description",
            "problem_statement",
            "intended_outcome",
            "primary_users",
            "goals",
            "non_goals",
            "mvp_scope",
            "post_mvp_scope",
            "out_of_scope",
            "core_flows",
            "constraints",
            "integrations",
            "raw_draft",
        )
        if not all(isinstance(getattr(self, name), str) for name in text_fields):
            raise ValueError("Project intake text fields must be strings.")
        if not isinstance(self.refinement, dict):
            raise ValueError("Refinement provenance must be a mapping.")
        if not isinstance(self.tech_stack, dict) or not all(
            isinstance(area, str) and isinstance(choice, TechChoice)
            for area, choice in self.tech_stack.items()
        ):
            raise ValueError("Technology stack must map area names to technology choices.")
        if not isinstance(self.commands, dict) or not all(
            isinstance(name, str) and isinstance(command, str)
            for name, command in self.commands.items()
        ):
            raise ValueError("Expected commands must map names to command strings.")
        for choice in self.tech_stack.values():
            choice.validate()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProjectIntake":
        if not isinstance(data, dict):
            raise ValueError("Project intake must be a YAML mapping.")
        values = dict(data or {})
        raw_stack = values.pop("tech_stack", {}) or {}
        if not isinstance(raw_stack, dict):
            raise ValueError("Technology stack must be a mapping.")
        try:
            intake = cls(**values)
        except TypeError as exc:
            raise ValueError(f"Invalid project intake fields: {exc}") from exc
        intake.tech_stack = default_tech_stack()
        for area, raw_choice in raw_stack.items():
            if area in intake.tech_stack:
                if not isinstance(raw_choice, dict):
                    raise ValueError(f"Technology choice {area} must be a mapping.")
                try:
                    intake.tech_stack[area] = TechChoice(**raw_choice)
                except TypeError as exc:
                    raise ValueError(f"Invalid technology choice {area}: {exc}") from exc
        if not isinstance(intake.commands, dict):
            raise ValueError("Expected commands must be a mapping.")
        if not all(
            isinstance(name, str) and isinstance(value, str)
            for name, value in intake.commands.items()
        ):
            raise ValueError("Expected command names and values must be strings.")
        intake.commands = {**default_commands(), **intake.commands}
        intake.validate()
        return intake

    def to_yaml(self) -> str:
        self.validate()
        return yaml.safe_dump(
            self.to_dict(), sort_keys=False, allow_unicode=True, default_flow_style=False
        )

    @classmethod
    def from_yaml(cls, content: str) -> "ProjectIntake":
        try:
            data = yaml.safe_load(content) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid intake YAML: {exc}") from exc
        return cls.from_dict(data)


@dataclass
class FactoryConfig:
    schema_version: int = 1
    enabled_tools: List[str] = field(default_factory=lambda: list(TOOL_IDS))
    default_refiner: Optional[str] = None
    refinement_timeout_seconds: int = 300
    factory_link_mode: str = "copy"
    integration_branch: str = "develop"
    storage_backend: str = "folder"
    storage_dsn: Optional[str] = None
    budget_enforcement: str = "warn"
    budgets: Dict[str, int] = field(default_factory=dict)

    def validate(self) -> None:
        if self.schema_version != 1:
            raise ValueError(f"Unsupported factory config schema: {self.schema_version}")
        if not isinstance(self.enabled_tools, list) or not all(
            isinstance(tool, str) for tool in self.enabled_tools
        ):
            raise ValueError("Enabled AI tools must be a list of tool IDs.")
        if self.default_refiner is not None and not isinstance(self.default_refiner, str):
            raise ValueError("Default refiner must be a tool ID or null.")
        invalid_tools = sorted(set(self.enabled_tools) - set(TOOL_IDS))
        if invalid_tools:
            raise ValueError(f"Unsupported AI tools: {', '.join(invalid_tools)}")
        if self.default_refiner and self.default_refiner not in self.enabled_tools:
            raise ValueError("Default refiner must be enabled.")
        if type(self.refinement_timeout_seconds) is not int:
            raise ValueError("Refinement timeout must be an integer.")
        if self.refinement_timeout_seconds < 1:
            raise ValueError("Refinement timeout must be positive.")
        if not isinstance(self.factory_link_mode, str):
            raise ValueError("Factory link mode must be a string.")
        if self.factory_link_mode not in {"copy", "submodule"}:
            raise ValueError("Factory link mode must be copy or submodule.")
        if not isinstance(self.integration_branch, str) or not self.integration_branch.strip():
            raise ValueError("Integration branch must not be empty.")
        if not isinstance(self.storage_backend, str) or not self.storage_backend.strip():
            raise ValueError("Storage backend must be a string.")
        if self.storage_dsn is not None and not isinstance(self.storage_dsn, str):
            raise ValueError("Storage DSN must be a connection string or null.")
        if not isinstance(self.budget_enforcement, str) or not self.budget_enforcement.strip():
            raise ValueError("Budget enforcement must be a string.")
        if not isinstance(self.budgets, dict):
            raise ValueError("Budgets must be a mapping.")

    def ignored_setting_warnings(self) -> List[str]:
        """Retired settings still accepted so older factory.yaml files load."""
        warnings: List[str] = []
        if self.storage_backend != "folder":
            warnings.append(
                f"storage_backend={self.storage_backend!r} is ignored; "
                "task state stays in Markdown files."
            )
        if (self.storage_dsn or "").strip():
            warnings.append("storage_dsn is ignored.")
        if self.budget_enforcement != "warn":
            warnings.append(
                f"budget_enforcement={self.budget_enforcement!r} is ignored."
            )
        if self.budgets:
            warnings.append("budgets are ignored.")
        return warnings

    def to_yaml(self) -> str:
        self.validate()
        return yaml.safe_dump(
            asdict(self), sort_keys=False, allow_unicode=True, default_flow_style=False
        )

    @classmethod
    def from_yaml(cls, content: str) -> "FactoryConfig":
        try:
            data = yaml.safe_load(content) or {}
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid factory config YAML: {exc}") from exc
        if not isinstance(data, dict):
            raise ValueError("Factory config must be a YAML mapping.")
        try:
            config = cls(**data)
        except TypeError as exc:
            raise ValueError(f"Invalid factory config fields: {exc}") from exc
        config.validate()
        return config


@dataclass
class RefinementResult:
    markdown: str
    assumptions: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)


@dataclass
class RefinementSettings:
    tool_id: str
    sections: List[str]
    timeout_seconds: int

    def validate(self) -> None:
        if self.tool_id not in TOOL_IDS:
            raise ValueError(f"Unsupported refinement tool: {self.tool_id}")
        if not self.sections:
            raise ValueError("Select at least one refinement section.")
        invalid_sections = sorted(set(self.sections) - set(REFINEMENT_SECTION_IDS))
        if invalid_sections:
            raise ValueError(
                f"Unsupported refinement sections: {', '.join(invalid_sections)}"
            )
        if type(self.timeout_seconds) is not int or self.timeout_seconds < 1:
            raise ValueError("Refinement timeout must be a positive integer.")


@dataclass
class ImportAction:
    path: str
    status: str
    reason: str
    proposed_content: Optional[str] = None


@dataclass
class ImportPlan:
    project_dir: str
    actions: List[ImportAction] = field(default_factory=list)

    @property
    def conflicts(self) -> List[ImportAction]:
        return [action for action in self.actions if action.status == "conflict"]

    @property
    def invalid(self) -> List[ImportAction]:
        return [action for action in self.actions if action.status == "invalid"]

    def render(self) -> str:
        lines = [f"Import plan: {self.project_dir}"]
        lines.extend(
            f"  {action.status.upper():8} {action.path} - {action.reason}"
            for action in self.actions
        )
        return "\n".join(lines)
