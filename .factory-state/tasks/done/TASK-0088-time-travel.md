# Task

## Metadata

- Project: superstep
- Task ID: TASK-0088
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: REQ-0051
- Design IDs: none
- Architecture IDs: DEC-0057

## Objective

Time travel: fork a run from a checkpoint.

## Scope

### In Scope

- backend/app/services/time_travel.py, services/run_service.py (_plan_fork, checkpoints, forked_from), routes/runs.py, core/errors.py; frontend time-travel-dialog.tsx, editor-run-panel.tsx, use-studio.ts; locales; e2e/time-travel.spec.ts; handbook run/traces, reference/api (en+vi).

### Out Of Scope

- Forking imported LangGraph graphs, waiting or running runs, and the final state.
- A persistent checkpoint store (events are the source).

## Dependencies

- None: based on develop.

## Activity Log

- 2026-10-24: implemented, verified with `factory deps apply` and `factory verify run --profile full` plus e2e and handbook builds (QA-0081); PR into develop.
- 2026-10-24: PR #133 merged into develop (0e1b43a); moved to done by TASK-0110.

## Handoff Notes

- Review REV-0081, QA-0081.
