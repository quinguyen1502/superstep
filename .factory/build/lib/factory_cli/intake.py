"""Load and merge non-interactive project intake.

`factory init --intake` and `--from-specs` exist so an agent can create a
project without the Textual wizard. Owner-provided values always win:
YAML and specs only fill blank fields, and a preset never overwrites them.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from .errors import FactoryError
from .models import ProjectIntake


# Headings from templates/project-specs-template.md mapped to intake fields.
_SPECS_TEXT_FIELDS: Dict[str, str] = {
    "one-line description": "one_line_description",
    "problem statement": "problem_statement",
    "intended outcome": "intended_outcome",
    "primary users": "primary_users",
    "goals": "goals",
    "non-goals": "non_goals",
    "mvp scope": "mvp_scope",
    "post-mvp scope": "post_mvp_scope",
    "out of scope": "out_of_scope",
    "core user flows": "core_flows",
    "constraints": "constraints",
    "integrations": "integrations",
}

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def read_text_file(path: Path, *, what: str) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FactoryError(f"Cannot read {what} {path}: {exc}") from exc


def load_intake_yaml(path: Path) -> ProjectIntake:
    content = read_text_file(path, what="intake file")
    try:
        return ProjectIntake.from_yaml(content)
    except ValueError as exc:
        raise FactoryError(f"Invalid intake file {path}: {exc}") from exc


def iter_markdown_sections(markdown: str) -> Iterable[Tuple[str, str]]:
    heading: Optional[str] = None
    body: List[str] = []
    for line in markdown.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            if heading is not None:
                yield heading, "\n".join(body).strip()
            heading = match.group(2).strip().lower()
            body = []
        else:
            body.append(line)
    if heading is not None:
        yield heading, "\n".join(body).strip()


def _section_text(body: str) -> str:
    items: List[str] = []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped or stripped in {"-", "*", "- Unknown", "* Unknown"}:
            continue
        if stripped.startswith(("- ", "* ")):
            item = stripped[2:].strip()
            if item and item.lower() != "unknown":
                items.append(item)
        elif not stripped.startswith("#"):
            items.append(stripped)
    return "\n".join(items)


def parse_specs_fields(markdown: str) -> Dict[str, str]:
    """Extract intake text fields from a project-specs-shaped document."""
    values: Dict[str, str] = {}
    for heading, body in iter_markdown_sections(markdown):
        field = _SPECS_TEXT_FIELDS.get(heading)
        if field is None:
            continue
        text = _section_text(body)
        if text:
            values[field] = text
    return values


def merge_specs_into_intake(intake: ProjectIntake, markdown: str) -> ProjectIntake:
    """Fill blank intake text fields from a specification. Never overwrite."""
    for field, value in parse_specs_fields(markdown).items():
        current = getattr(intake, field)
        if isinstance(current, str) and not current.strip():
            setattr(intake, field, value)
    return intake


def overlay_cli_intake(
    intake: ProjectIntake,
    *,
    project_name: str,
    tools: List[str],
    refiner: Optional[str],
    tool_kit_level: Optional[str],
    tools_explicit: bool,
    refiner_explicit: bool,
) -> ProjectIntake:
    """Apply CLI flags on top of a loaded or default intake."""
    intake.project_name = project_name
    if tools_explicit:
        intake.tools = list(tools)
    elif not intake.tools:
        intake.tools = list(tools)
    if refiner_explicit:
        intake.refiner = refiner
        intake.use_ai = bool(refiner)
    elif intake.refiner:
        intake.use_ai = True
    if tool_kit_level:
        intake.tool_kit_level = tool_kit_level
    return intake
