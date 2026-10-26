from __future__ import annotations

from datetime import date
from typing import Dict, Iterable, List

from .adapters import get_adapter
from .guidance import PROJECT_PRESETS, analyze_compatibility
from .models import FactoryConfig, ProjectIntake, TechChoice
from .stacks import find_stack


def _items(value: str) -> List[str]:
    items = []
    for line in value.splitlines():
        item = line.strip().lstrip("-* ").strip()
        if item:
            items.append(item)
    return items


def _bullets(value: str, fallback: str = "Unknown") -> str:
    items = _items(value)
    return "\n".join(f"- {item}" for item in items) if items else f"- {fallback}"


def _single(value: str, fallback: str = "Unknown") -> str:
    return value.strip() or fallback


def _proposed_requirements(value: str) -> str:
    items = _items(value)
    if not items:
        return "- Unknown"
    return "\n".join(f"- [Proposed] {item}" for item in items)


def _compatibility_lines(intake: ProjectIntake) -> str:
    insights = analyze_compatibility(intake)
    if not insights:
        return "- No deterministic compatibility insights for the current selections."
    lines: List[str] = []
    for insight in insights:
        lines.append(f"- [{insight.level.title()}] **{insight.title}:** {insight.message}")
        if insight.recommendation:
            lines.append(f"  - Recommendation: {insight.recommendation}")
        for question in insight.questions:
            lines.append(f"  - Open question: {question}")
    return "\n".join(lines)


def render_confidence_review(intake: ProjectIntake, heading_level: int = 1) -> str:
    approved = [
        f"{area.replace('_', ' ').title()}: {choice.value}"
        for area, choice in intake.tech_stack.items()
        if choice.value.strip() and choice.status == "Approved"
    ]
    needs_attention = [
        f"{area.replace('_', ' ').title()}: {_single(choice.value)} [{choice.status}]"
        for area, choice in intake.tech_stack.items()
        if choice.status != "Approved"
    ]
    expected = [
        f"{name.replace('_', ' ').title()}: {command} [Expected]"
        for name, command in intake.commands.items()
        if command.strip()
    ]
    refinement = intake.refinement or {}
    assumptions = [str(value) for value in refinement.get("assumptions", [])]
    open_questions = [str(value) for value in refinement.get("open_questions", [])]
    heading = "#" * heading_level
    subheading = "#" * (heading_level + 1)
    lines = [
        f"{heading} Decision and confidence review",
        "",
        "Focus review on uncertain or inferred content; `Approved` remains owner-only.",
        "",
        f"{subheading} Owner-confirmed decisions",
        "",
        *(f"- {item}" for item in approved),
    ]
    if not approved:
        lines.append("- None yet.")
    lines.extend(("", f"{subheading} Needs attention", ""))
    lines.extend(f"- {item}" for item in needs_attention)
    if not needs_attention:
        lines.append("- No unresolved technology choices.")
    lines.extend(("", f"{subheading} Commands awaiting repository evidence", ""))
    lines.extend(f"- {item}" for item in expected)
    if not expected:
        lines.append("- No expected commands recorded.")
    lines.extend(("", f"{subheading} Architecture and compatibility insights", "", _compatibility_lines(intake)))
    lines.extend(("", f"{subheading} AI assumptions", ""))
    lines.extend(f"- {item}" for item in assumptions)
    if not assumptions:
        lines.append("- None reported.")
    lines.extend(("", f"{subheading} AI open questions", ""))
    lines.extend(f"- {item}" for item in open_questions)
    if not open_questions:
        lines.append("- None reported.")
    return "\n".join(lines).rstrip() + "\n"


def render_project_specs(intake: ProjectIntake) -> str:
    intake.validate()
    stack_lines = []
    for area, choice in intake.tech_stack.items():
        stack = find_stack(area, choice.value)
        automation = (
            ", ".join(stack.capabilities)
            if stack and stack.capabilities
            else "specification only"
        )
        stack_lines.append(
            f"- {area.replace('_', ' ').title()}: {_single(choice.value)} "
            f"[{choice.status}]; Factory automation: {automation}"
        )
    command_lines = []
    for name, command in intake.commands.items():
        value = f"{command} [Expected]" if command.strip() else "Unknown"
        command_lines.append(f"- {name.replace('_', ' ').title()}: {value}")
    raw_section = ""
    if intake.raw_draft.strip():
        raw_section = f"""
## Source Draft

The following owner-provided notes remain source material and are not automatically approved decisions.

{intake.raw_draft.strip()}
"""

    preset = PROJECT_PRESETS.get(intake.project_preset, {})
    preset_label = str(preset.get("label", "None"))
    assumption_lines = [
        "- Technology choices not marked `Approved` are not binding decisions.",
        "- Commands marked `Expected` are not observed until source files confirm them.",
    ]
    question_lines = [
        "- Confirm every `Preferred`, `Proposed`, or `Unknown` technology choice before implementation requires it."
    ]
    approved_summary = "\n".join(
        f"{area.replace('_', ' ').title()}: {choice.value}"
        for area, choice in intake.tech_stack.items()
        if choice.value.strip() and choice.status == "Approved"
    )
    attention_summary = "\n".join(
        f"{area.replace('_', ' ').title()}: {_single(choice.value)} [{choice.status}]"
        for area, choice in intake.tech_stack.items()
        if choice.status != "Approved"
    )

    return f"""# Project Specs

Statements marked `Approved` are owner decisions. `Preferred`, `Proposed`, and `Unknown` items require confirmation or discovery.

## Summary

### Project Name

- {intake.project_name}

### One-Line Description

- {_single(intake.one_line_description)}

### Problem Statement

{_single(intake.problem_statement)}

### Intended Outcome

{_single(intake.intended_outcome)}

### Starter Preset

- {preset_label} [Input aid; not an architectural decision]

## Vision

### Goals

{_bullets(intake.goals)}

### Non-Goals

{_bullets(intake.non_goals)}

### Success Metrics

- Unknown; define measurable product and delivery outcomes before MVP approval.

## Users And Stakeholders

### Primary Users

{_bullets(intake.primary_users)}

## Scope

### MVP Scope

{_bullets(intake.mvp_scope)}

### Post-MVP Scope

{_bullets(intake.post_mvp_scope)}

### Out Of Scope

{_bullets(intake.out_of_scope)}

## Roadmap

### P0

{_bullets(intake.mvp_scope)}

### P1

{_bullets(intake.post_mvp_scope)}

### P2

- Unknown

## Core User Flows

{_bullets(intake.core_flows)}

### Required Flow States

- Loading, empty, error, permission, and completion states: Unknown.

## Features

### Candidate MVP Requirements

{_proposed_requirements(intake.mvp_scope)}

### Acceptance Criteria

- Unknown; refine each approved requirement into verifiable acceptance criteria.

## UX/UI Direction

### Product Experience

- Unknown

### Screens Or Surfaces

- Derive from approved user flows.

### Accessibility Requirements

- Unknown; define keyboard, screen-reader, contrast, and responsive expectations where applicable.

## Data And Domain Model

### Main Entities And Relationships

- Unknown; derive from approved requirements without treating draft nouns as decisions.

### Data Lifecycle, Privacy, And Compliance

- Unknown

## Technical Direction

### Technology Stack

{chr(10).join(stack_lines)}

### Expected Commands

{chr(10).join(command_lines)}

### Constraints

{_bullets(intake.constraints)}

### Integrations

{_bullets(intake.integrations)}

### Architecture And Compatibility Insights

{_compatibility_lines(intake)}

### Explicit Technical Decisions

- Only technology choices marked `Approved` may generate decision records.

## Quality Attributes

### Performance

- Unknown

### Reliability

- Unknown

### Security And Privacy

- Unknown

### Maintainability And Observability

- Unknown

## Delivery And Operations

### Environments And Release Expectations

- Unknown

### Monitoring, Rollback, And Recovery

- Unknown

## Risks And Assumptions

### Assumptions

{chr(10).join(assumption_lines)}

### Risks And Blockers

- Unknown

### Open Questions

{chr(10).join(question_lines)}

## Validation Strategy

- Confirm project artifacts preserve the statuses and constraints in this specification.
- Discover actual install, run, test, build, lint, typecheck, format, and migration commands from source files.
- Define requirement-level automated tests, manual QA, and acceptance evidence before implementation completion.

## Initial Work Breakdown

### Suggested Tasks

{_proposed_requirements(intake.mvp_scope)}

## Decision And Confidence Summary

### Owner-Confirmed Technology

{_bullets(approved_summary, 'None yet')}

### Items Requiring Attention

{_bullets(attention_summary, 'None')}

### Evidence State

- Technology values are declared owner inputs, not repository observations.
- Populated commands are `Expected` until verified against repository evidence.
{raw_section}
"""


def render_vision(intake: ProjectIntake) -> str:
    return f"""# Vision

## Project

{intake.project_name}

## Problem Statement

{_single(intake.problem_statement)}

## High-Level Idea

{_single(intake.intended_outcome or intake.one_line_description)}

## Goals

{_bullets(intake.goals)}

## Non-Goals

{_bullets(intake.non_goals)}

## Notes

Technical direction is recorded separately and retains its approval status.
"""


def render_project(intake: ProjectIntake) -> str:
    stack_lines = []
    open_questions = []
    for area, choice in intake.tech_stack.items():
        stack_lines.append(
            f"- {area.replace('_', ' ').title()}: {_single(choice.value)} ({choice.status}; declared, not observed)"
        )
        if choice.status != "Approved":
            open_questions.append(
                f"Confirm {area.replace('_', ' ')} technology; current status is {choice.status}."
            )
    command_lines = []
    for name, command in intake.commands.items():
        command_lines.append(
            f"- {name.replace('_', ' ').title()}: "
            + (f"{command} (Expected)" if command.strip() else "Unknown")
        )
    return f"""# Project

## Name

{intake.project_name}

## Domain

- {_single(intake.one_line_description)}

## Actors

{_bullets(intake.primary_users)}

## Modules

- To be discovered from approved scope and implementation.

## Constraints

{_bullets(intake.constraints)}

## Declared Technology Direction

{chr(10).join(stack_lines)}

## Technology Discovery

{chr(10).join(command_lines)}

## Assumptions

- Declared technology is not observed evidence until implementation files exist.

## Open Questions

{chr(10).join(f'- {item}' for item in open_questions) if open_questions else '- None.'}
"""


def render_roadmap(intake: ProjectIntake) -> str:
    return f"""# Roadmap

## P0

{_bullets(intake.mvp_scope)}

## P1

{_bullets(intake.post_mvp_scope)}

## P2

- To be defined after the MVP baseline is validated.
"""


def render_discovery(intake: ProjectIntake) -> str:
    stack_lines = [
        f"- {area.replace('_', ' ').title()}: {_single(choice.value)}; status={choice.status}; evidence=owner intake"
        for area, choice in intake.tech_stack.items()
    ]
    command_lines = [
        f"- {name.replace('_', ' ').title()}: "
        + (f"{command}; evidence=owner-declared expected command" if command.strip() else "Unknown")
        for name, command in intake.commands.items()
    ]
    return f"""# Discovery: Initial Project Context

## Metadata

- Discovery ID: DISC-0001
- Project: {intake.project_name}
- Date: {date.today().isoformat()}
- Source: project initialization intake

## Observed Context

- No source implementation was generated by factory initialization.

## Declared Technology Direction

{chr(10).join(stack_lines)}

## Commands

{chr(10).join(command_lines)}

## Gaps And Open Questions

- Verify every command and technology choice against implementation evidence.
- Resolve all choices not marked Approved before relying on them.
"""


def render_decision(intake: ProjectIntake, area: str, choice: TechChoice, index: int) -> str:
    return f"""# Decision

## Metadata

- Decision ID: DEC-{index:04d}
- Project: {intake.project_name}
- Status: Approved
- Date: {date.today().isoformat()}

## Context

The owner approved the {area.replace('_', ' ')} technology during project initialization.

## Decision

Use {choice.value} for {area.replace('_', ' ')}.

## Rationale

- Owner-approved project constraint from `project-specs.md`.

## Tradeoffs And Impacts

- Validate compatibility and commands during the first discovery task.
"""


def render_standard(title: str) -> str:
    return f"""# {title} Standards

Document project-specific {title.lower()} standards here after they are discovered or approved.

## Current Standards

- Unknown

## Assumptions

- None

## Open Questions

- Which project evidence or owner decision defines this standard?
"""


def render_agents() -> str:
    return """# Project Agents

This project uses the AI Software Factory framework in `.factory/`. This file is the canonical project instruction entrypoint for Codex, Cursor, and Grok. Claude Code imports it through `.claude/CLAUDE.md`.

Init creates a valid factory skeleton. It is not ready for implementation until `factory ready` passes.

## Required Rules

- Before applying factory workflows, verify `.factory/AGENTS.md` exists and read it.
- If `.factory/AGENTS.md` is missing and `.factory` is configured as a submodule, initialize it with `git submodule update --init .factory`.
- If initialization requires credentials, network access, or approval, request it before implementation.
- If `.factory/AGENTS.md` remains unavailable, stop implementation and record a blocker in `.factory-state/`.
- Read `vision.md`, `project.md`, `roadmap.md`, and the current task before work.
- Treat `project-specs.md` as source onboarding context and preserve explicit approval statuses.
- Discover project context and commands from repository evidence; do not treat expected commands as observed.
- Read `.factory-state/artifacts/` selectively by following task and artifact references.
- Store generated workflow state under `.factory-state/`, never `.factory/`.
- Record assumptions, blockers, open questions, review results, and QA evidence in artifacts.
- Do not create standalone tasks or blocker artifacts for command trials, missing local authentication, sandbox or network retries, or other transient assistant execution mechanics unless they materially block an active delivery task.
- Allocate new artifact IDs after `git fetch --all --prune` with `factory ids next <TYPE> --all-refs`. Do not guess the next number.
- Use task branches named `factory/task-<id>-<short-name>` unless project standards define another convention.
- Do not merge without explicit human approval.
- Do not start implementation source work until `factory ready` exits 0, unless the owner explicitly overrides that gate.

## Workflow Skills

Use the matching installed skill when the user asks for that job. If the skill files are missing, run `factory skills apply`.

- `onboard-specs` — convert `project-specs.md` into vision, project, roadmap, REQ/DES/ARCH, and tasks.
- `create-requirement` — write one requirement artifact.
- `plan-tasks` — split an approved requirement into verifiable tasks.
- `discuss` — analysis only; no edits.
- `next-task` — recommend the next lifecycle task.
- `task-start` — branch and move a task to doing; do not implement.
- `scoped-change` — implement or fix, then stop before validation.
- `task-validation` — run declared project checks.
- `task-review` — write a review artifact.
- `task-qa` — write a QA artifact.
- `finish-pr` — rebase, squash, and mark the existing PR Ready.
- `cleanup-branches` — prune merged or obsolete local branches.

## Factory References

- Shared behavior: `.factory/AGENTS.md`
- Agent roles: `.factory/agents/`
- Workflows: `.factory/workflows/`
- Templates: `.factory/templates/`
- Framework docs: `.factory/docs/`
"""


def render_task(
    project: str,
    task_id: str,
    title: str,
    status: str,
    objective: str,
    expected_outputs: Iterable[str],
    validation_plan: Iterable[str],
) -> str:
    today = date.today().isoformat()
    branch_id = task_id.lower()
    if branch_id.startswith("task-"):
        branch_id = branch_id[5:]
    branch_name = f"factory/task-{branch_id}-{slugify(title)}"
    return f"""# Task

## Metadata

- Project: {project}
- Task ID: {task_id}
- Status: {status}
- Owner:
- Created: {today}
- Updated: {today}
- Requirement IDs:
- Design IDs:
- Architecture IDs:

## Objective

{objective}

## Scope

### In Scope

- {title}

### Out Of Scope

- Source implementation outside the approved task.

## Inputs

- `project-specs.md`
- `vision.md`
- `project.md`
- `roadmap.md`

## Related Artifacts

- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`

## Expected Outputs

{chr(10).join(f'- {item}' for item in expected_outputs)}

## Constraints

- Preserve explicit technology approval statuses.

## Dependencies

- None

## Acceptance Criteria

- Project context and commands are supported by evidence or explicitly marked unknown.

## Validation Plan

{chr(10).join(f'- {item}' for item in validation_plan)}

## Assumptions

- None

## Open Questions

- Which expected commands are confirmed by implementation evidence?

## Activity Log

- {today}: Created task.

## Handoff Notes

- Use branch `{branch_name}` when implementation begins.
"""


def render_initial_task(intake: ProjectIntake) -> str:
    return render_task(
        project=intake.project_name,
        task_id="TASK-0001",
        title="Confirm project context and technical baseline",
        status="backlog",
        objective=(
            "Validate the owner-approved specification, declared technology direction, expected "
            "commands, standards, and unresolved questions before source implementation begins."
        ),
        expected_outputs=(
            "Updated project context with observed evidence.",
            "Confirmed or corrected project commands and technology statuses.",
            "Follow-up artifacts and backlog tasks linked from this task.",
        ),
        validation_plan=(
            "Run factory validate.",
            "Confirm observed claims cite repository evidence.",
        ),
    )


def slugify(value: str) -> str:
    result: List[str] = []
    previous_dash = False
    for character in value.lower():
        if character.isalnum():
            result.append(character)
            previous_dash = False
        elif not previous_dash:
            result.append("-")
            previous_dash = True
    return "".join(result).strip("-") or "task"


def render_factory_config(config: FactoryConfig) -> str:
    return config.to_yaml()


def render_bundle(intake: ProjectIntake, config: FactoryConfig) -> Dict[str, str]:
    from .tooling import default_tool_policy, render_tooling_bundle

    tool_policy = default_tool_policy(
        config.enabled_tools,
        level=intake.tool_kit_level,
        commands=intake.commands,
    )
    bundle: Dict[str, str] = {
        "AGENTS.md": render_agents(),
        "project-specs.md": render_project_specs(intake),
        "vision.md": render_vision(intake),
        "project.md": render_project(intake),
        "roadmap.md": render_roadmap(intake),
        ".factory-state/factory.yaml": render_factory_config(config),
        ".factory-state/intake/project-specs-input.yaml": intake.to_yaml(),
        ".factory-state/artifacts/DISC-0001-project-context.md": render_discovery(intake),
        ".factory-state/tasks/backlog/TASK-0001-confirm-project-context.md": render_initial_task(intake),
        **render_tooling_bundle(tool_policy),
    }
    for tool_id in config.enabled_tools:
        bundle.update(get_adapter(tool_id).instruction_assets())
    for index, (area, choice) in enumerate(
        (
            (area, choice)
            for area, choice in intake.tech_stack.items()
            if choice.status == "Approved" and choice.value.strip()
        ),
        start=1,
    ):
        bundle[f".factory-state/decisions/DEC-{index:04d}-{slugify(area)}.md"] = render_decision(
            intake, area, choice, index
        )
    return bundle
