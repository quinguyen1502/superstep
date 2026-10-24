# Task

## Metadata

- Project: superstep
- Task ID: TASK-0100
- Status: done (backfilled)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-23
- Updated: 2026-10-24
- Requirement IDs: REQ-0045, REQ-0046, REQ-0047, REQ-0059
- Design IDs: none
- Architecture IDs: none
- Pull request: [#114](https://github.com/quinguyen1502/superstep/pull/114) `factory/version-0.4.0`
- Merge commit: `dd12c7061c16b87249d33dc840b275ce1a75ef6b` (2026-10-23)

## Objective

Version 0.4.0.

> Backfilled 2026-10-24 (TASK-0093): reconstructed from the PR description and diff after the fact; the work was merged outside the factory workflow, so no task, review or QA record existed at the time.

## Scope (from the PR)

- TypeScript in Code mode on Deno: language registry, sandbox image `studio-code-ts:1`, editor support (REQ-0046, #109–#111);
- LangGraph.js TypeScript export (REQ-0047, #112);
- Superstep brand: logo, favicons and tokens (DEC-0047, #108);
- Vietnamese glossary and locale polish (REQ-0045, #107);
- fix: settling a run survives a cancelled handler (#113).

## Changed files

- 3 files: `backend/pyproject.toml`, `frontend/package-lock.json`, `frontend/package.json`.

## Activity Log

- 2026-10-23: merged into develop (dd12c70).
- 2026-10-24: task record backfilled (TASK-0093); verified retroactively on develop by QA-0085.

## Handoff Notes

- Review REV-0092, QA QA-0092 (retroactive records).
