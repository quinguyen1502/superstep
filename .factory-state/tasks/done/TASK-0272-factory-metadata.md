# Task

## Metadata

- Project: superstep
- Task ID: TASK-0272
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0089
- Plan: PLAN-0009
- Size: S

## Objective

Make factory metadata honest: record the missing TASK-0253 review, give the later duplicate REV/QA records new ids, and reconcile merged task statuses.

## Scope

### In Scope

- Write the missing review and QA for merged TASK-0253 from the files on `develop` and one handbook check. Do not invent the original CI counts.
- Keep REV-0242 and QA-0242 on TASK-0259, because PR #320 merged before PR #321. Move the TASK-0251 copies to REV-0255 and QA-0255.
- Keep REV-0251 and QA-0251 on TASK-0269, because PR #331 merged before PR #329. Move the TASK-0261 copies to REV-0256 and QA-0256.
- Record that PR #334 and PR #333 are merged, and that the owner closed AC11. Do not mark REQ-0086 or REQ-0089 done.

### Out Of Scope

- Product code, browser export helpers, and TASK-0227.
- Deleting old branches that still contain the previous filenames.

## Activity Log

- 2026-11-07: Planned on PLAN-0009 after the owner said "Làm đi".
- 2026-11-07: PR #333 merged (`bbbd23b2`). Review REV-0258. QA QA-0258. Status done. Not merged.
- 2026-11-07: `factory validate` passed on this worktree after linking the gitignored virtualenv and `node_modules`. Warnings only: lockfile drift, and no non-discovery task in todo with acceptance criteria. The TASK-0253 missing-review error is gone. `factory verify` is left to CI because the local virtualenv is x86_64.

## Handoff Notes

- Branch: `factory/task-0272-factory-metadata`.
- Review: `.factory-state/artifacts/REV-0258-TASK-0272-factory-metadata.md`. QA: `.factory-state/artifacts/QA-0258-TASK-0272-factory-metadata.md`.
- TASK-0253 review: `.factory-state/artifacts/REV-0257-TASK-0253-browser-e2e-handbook.md`. QA: `.factory-state/artifacts/QA-0257-TASK-0253-browser-e2e-handbook.md`.
- REQ-0086 and REQ-0089 are not marked done.
