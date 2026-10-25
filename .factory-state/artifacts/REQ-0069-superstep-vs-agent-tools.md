# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0069
- Status: In review (TASK-0113)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Source: owner request in chat, 2026-10-25 ("Tạo tài liệu so sánh với n8n, dify, crewai, pydanticai").

## Summary

- A handbook page (en+vi) comparing Superstep with n8n, Dify, CrewAI and PydanticAI, modelled on the
  Superstep vs LangSmith page (REQ-0052), citing each project's official docs and license file.

## Acceptance Criteria

- Page `reference/superstep-vs-agent-tools.md` in en and vi, in both navs and the reference index; no emoji.
- A summary comparison table (approach, LangGraph, license, self-hosting, human in the loop, durable runs and
  time travel, tests/evals/observability, API and SDK, code export) plus a section per tool, "using them
  together" and "when to choose another tool" guidance.
- Licenses stated from the license files: n8n Sustainable Use License, Dify modified Apache 2.0 with conditions,
  CrewAI MIT, PydanticAI MIT. Claims about Superstep match README/CHANGELOG; unknowns are marked, not guessed.
- Sources re-checked on 2026-10-25; strict handbook builds pass with no warnings; CHANGELOG Unreleased.

## Out Of Scope

- Pricing of the other products; feature claims not in the cited sources.
