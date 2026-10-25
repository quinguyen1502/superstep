# Task

## Metadata

- Project: superstep
- Task ID: TASK-0113
- Status: review (PR)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Requirement IDs: REQ-0069
- Design IDs: none
- Architecture IDs: none

## Objective

Handbook: Superstep vs visual builders (n8n, Dify, Langflow, Flowise) and Superstep vs agent frameworks (CrewAI,
PydanticAI).

## Scope

### In Scope

- handbook/docs/{en,vi}/reference/superstep-vs-visual-builders.md and superstep-vs-agent-frameworks.md,
  reference/index.md, mkdocs.yml, mkdocs.vi.yml,
  CHANGELOG.md.
- Merged TASK-0112 (#140) moved to `done`.

### Out Of Scope

- Pricing; feature claims beyond the cited sources.

## Dependencies

- None: based on develop at f7e466c; links only to pages that exist on develop.

## Activity Log

- 2026-10-25: sources fetched, page written (en, vi), strict handbook builds clean, verified with
  `factory deps apply` and `factory verify run --profile full` (QA-0105); PR #141 into develop.
- 2026-10-25: scope change from the owner: split into a visual-builders page (adds Langflow and Flowise) and an
  agent-frameworks page; old `superstep-vs-agent-tools.md` removed; re-verified (QA-0105).

## Handoff Notes

- Review REV-0105, QA-0105.
