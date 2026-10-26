# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0069
- Status: Done (TASK-0113, PR #141)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Source: owner request in chat, 2026-10-25 ("Tạo tài liệu so sánh với n8n, dify, crewai, pydanticai").

## Summary

- Two handbook pages (en+vi), modelled on Superstep vs LangSmith (REQ-0052), citing each project's official docs
  and license file. Scope change 2026-10-25 (owner decision): the single page was split in two and Langflow and
  Flowise were added.

## Acceptance Criteria

- `reference/superstep-vs-visual-builders.md` (n8n, Dify, Langflow, Flowise: the visual, low-code competitors) and
  `reference/superstep-vs-agent-frameworks.md` (CrewAI, PydanticAI, framed as Superstep plus LangGraph against a
  code-first framework) in en and vi, in both navs and both reference indexes; the earlier
  `superstep-vs-agent-tools.md` removed with no stale links; no emoji.
- Summary tables of at most five columns, a section per tool, "using them together" and "when to choose another
  tool" guidance.
- Licenses from the license files: n8n Sustainable Use License, Dify Apache 2.0 with conditions, Langflow MIT,
  Flowise Apache 2.0 except the enterprise directory, CrewAI MIT, PydanticAI MIT, LangGraph MIT. Claims about
  Superstep match README/CHANGELOG; unknowns are marked "not covered by the sources".
- Sources re-checked on 2026-10-25; strict handbook builds pass with no issues; CHANGELOG Unreleased.

## Out Of Scope

- Pricing of the other products; feature claims not in the cited sources.
