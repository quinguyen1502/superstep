"""Emit reusable skill files for enabled AI coding tools.

The framework ships `SKILL.md` templates under `templates/skills/<name>/`.
This module discovers those templates and produces per-tool assets:

- Claude Code: `.claude/skills/<name>/SKILL.md` (byte-identical copy).
- Cursor:      `.cursor/rules/<name>.mdc` (frontmatter converted).
- Codex:       `.agents/skills/<name>/SKILL.md` plus a generated
               `agents/openai.yaml` adapter alongside it.
- Grok:        `.grok/skills/<name>/SKILL.md` (byte-identical copy).

Design mirrors the existing `plan / apply / validate` pattern used by
`tools`, `scaffold`, `deps`, and `stack` commands.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from .constants import TOOL_IDS


SKILL_TEMPLATES_ROOT = "templates/skills"


@dataclass
class SkillAsset:
    """A single file to emit for a tool."""

    skill: str
    tool_id: str
    path: str
    content: str


@dataclass
class SkillPlanEntry:
    asset: SkillAsset
    status: str  # "create" | "keep" | "conflict"
    reason: str = ""


@dataclass
class SkillPlan:
    entries: List[SkillPlanEntry] = field(default_factory=list)

    @property
    def creates(self) -> List[SkillPlanEntry]:
        return [e for e in self.entries if e.status == "create"]

    @property
    def keeps(self) -> List[SkillPlanEntry]:
        return [e for e in self.entries if e.status == "keep"]

    @property
    def conflicts(self) -> List[SkillPlanEntry]:
        return [e for e in self.entries if e.status == "conflict"]

    def render(self) -> str:
        if not self.entries:
            return "Skills plan: no skill templates found in .factory/templates/skills/."
        lines = ["Skills plan:"]
        by_tool: Dict[str, List[SkillPlanEntry]] = {}
        for entry in self.entries:
            by_tool.setdefault(entry.asset.tool_id, []).append(entry)
        for tool_id in sorted(by_tool):
            lines.append(f"  {tool_id}:")
            for entry in by_tool[tool_id]:
                label = f"[{entry.status}]".ljust(11)
                lines.append(f"    {label}{entry.asset.path}")
        lines.append(
            f"Summary: {len(self.creates)} create, {len(self.keeps)} keep, "
            f"{len(self.conflicts)} conflict."
        )
        return "\n".join(lines)


@dataclass
class SkillApplyResult:
    created: List[str] = field(default_factory=list)
    kept: List[str] = field(default_factory=list)
    overwritten: List[str] = field(default_factory=list)
    conflicts_preserved: List[str] = field(default_factory=list)

    @property
    def had_conflicts(self) -> bool:
        return bool(self.conflicts_preserved)


class SkillError(Exception):
    """Raised when skill discovery or emission fails."""


def discover_templates(factory_root: Path) -> List[Path]:
    """Return sorted list of SKILL.md template paths under the framework root."""
    root = factory_root / SKILL_TEMPLATES_ROOT
    if not root.is_dir():
        return []
    return sorted(root.glob("*/SKILL.md"))


_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n(.*)$", re.DOTALL)


def _split_frontmatter(content: str) -> Tuple[Dict[str, str], str]:
    match = _FRONTMATTER_RE.match(content)
    if not match:
        raise SkillError("SKILL.md is missing YAML frontmatter")
    fm_text, body = match.group(1), match.group(2)
    fm: Dict[str, str] = {}
    for line in fm_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        fm[key.strip()] = value.strip()
    return fm, body


def _humanize(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


def _cursor_asset(skill: str, source_content: str) -> SkillAsset:
    fm, body = _split_frontmatter(source_content)
    description = fm.get("description", "").strip()
    mdc = (
        "---\n"
        f"description: {description}\n"
        "alwaysApply: false\n"
        "---\n"
        f"\n{body}"
    )
    return SkillAsset(
        skill=skill,
        tool_id="cursor",
        path=f".cursor/rules/{skill}.mdc",
        content=mdc,
    )


def _codex_openai_yaml(skill: str, source_content: str) -> str:
    fm, _ = _split_frontmatter(source_content)
    description = fm.get("description", "").strip()
    short = description
    if len(short) > 90:
        short = short[:87].rsplit(" ", 1)[0] + "..."
    display = _humanize(skill)
    return (
        "interface:\n"
        f'  display_name: "{display}"\n'
        f'  short_description: "{short}"\n'
        f'  default_prompt: "Use ${skill} to apply the {display} workflow."\n'
        "\n"
        "policy:\n"
        "  allow_implicit_invocation: false\n"
    )


def assets_for_tool(tool_id: str, skill: str, source_content: str) -> List[SkillAsset]:
    if tool_id in {"claude-code", "grok"}:
        root = ".claude" if tool_id == "claude-code" else ".grok"
        return [
            SkillAsset(
                skill=skill,
                tool_id=tool_id,
                path=f"{root}/skills/{skill}/SKILL.md",
                content=source_content,
            )
        ]
    if tool_id == "cursor":
        return [_cursor_asset(skill, source_content)]
    if tool_id == "codex":
        return [
            SkillAsset(
                skill=skill,
                tool_id=tool_id,
                path=f".agents/skills/{skill}/SKILL.md",
                content=source_content,
            ),
            SkillAsset(
                skill=skill,
                tool_id=tool_id,
                path=f".agents/skills/{skill}/agents/openai.yaml",
                content=_codex_openai_yaml(skill, source_content),
            ),
        ]
    return []


def _classify(target: Path, expected: str) -> Tuple[str, str]:
    if not target.exists():
        return "create", ""
    try:
        current = target.read_text(encoding="utf-8")
    except OSError as exc:
        return "conflict", f"cannot read existing file: {exc}"
    if current == expected:
        return "keep", "matches template"
    return "conflict", "existing file differs from template"


def plan_skills(
    project_dir: Path,
    factory_root: Path,
    enabled_tools: List[str],
    only: Optional[List[str]] = None,
) -> SkillPlan:
    invalid = sorted(set(enabled_tools) - set(TOOL_IDS))
    if invalid:
        raise SkillError(f"Unsupported AI tools: {', '.join(invalid)}")
    templates = discover_templates(factory_root)
    if only is not None:
        only_set = set(only)
        templates = [t for t in templates if t.parent.name in only_set]
        missing = only_set - {t.parent.name for t in templates}
        if missing:
            raise SkillError(
                f"Requested skills not found in templates: {', '.join(sorted(missing))}"
            )
    plan = SkillPlan()
    for source in templates:
        skill = source.parent.name
        try:
            content = source.read_text(encoding="utf-8")
        except OSError as exc:
            raise SkillError(f"Cannot read {source}: {exc}") from exc
        try:
            _split_frontmatter(content)
        except SkillError as exc:
            raise SkillError(f"{source}: {exc}") from exc
        for tool_id in enabled_tools:
            for asset in assets_for_tool(tool_id, skill, content):
                target = project_dir / asset.path
                status, reason = _classify(target, asset.content)
                plan.entries.append(SkillPlanEntry(asset=asset, status=status, reason=reason))
    return plan


def apply_plan(
    project_dir: Path,
    plan: SkillPlan,
    force: bool = False,
) -> SkillApplyResult:
    from .project import atomic_write  # avoid circular import at module load

    result = SkillApplyResult()
    for entry in plan.entries:
        target = project_dir / entry.asset.path
        if entry.status == "keep":
            result.kept.append(entry.asset.path)
            continue
        if entry.status == "conflict" and not force:
            result.conflicts_preserved.append(entry.asset.path)
            continue
        atomic_write(target, entry.asset.content)
        if entry.status == "create":
            result.created.append(entry.asset.path)
        else:
            result.overwritten.append(entry.asset.path)
    return result


def render_apply_summary(result: SkillApplyResult) -> str:
    lines = [
        f"Created: {len(result.created)}",
        f"Kept: {len(result.kept)}",
        f"Overwritten: {len(result.overwritten)}",
        f"Conflicts preserved: {len(result.conflicts_preserved)}",
    ]
    if result.conflicts_preserved:
        lines.append("Conflicts preserved (re-run with --force to overwrite):")
        for path in result.conflicts_preserved:
            lines.append(f"  - {path}")
    return "\n".join(lines)
