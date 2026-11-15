# Task

## Metadata

- Project: superstep
- Task ID: TASK-0273
- Title: Export per-node LLM credential slots
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0090
- Design IDs:
- Architecture IDs: DEC-0089

## Objective

Give each exported model credential a stable `LLM_CRED_<n>` slot. The credential id is never written. An unset slot keeps `LLM_PROVIDER`.

## Scope

### In Scope

- LLM, fallback, attachment, Agent and Decision calls in Python and TypeScript.

### Out Of Scope

- Cross-language code nodes.
- Approval and managed connections except the shared branch (TASK-0274, TASK-0275).

## Inputs

- REQ-0090, DEC-0089, PLAN-0010

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0090-export-remaining-runtime.md`
- Design:
- Architecture:
- Decisions: `.factory-state/decisions/DEC-0089-export-remaining-runtime.md`
- Discovery:
- Clarifications:

## Expected Outputs

- Slot parameters on the model helpers and calls that pass a slot only when a credential exists.

## Implementation Notes

- Lands on `factory/req-0090-export-remaining` with TASK-0274 and TASK-0275.

## Constraints

- Do not print credential ids. Do not change failover when the slot environment is unset.

## Dependencies

- None.

## Acceptance Criteria

- Two credentials become `LLM_CRED_1` and `LLM_CRED_2`. The ids are absent.
- A set slot provider and key are selected. A missing key names `<SLOT>_API_KEY`.
- An unset slot still uses `LLM_PROVIDER`, including the existing fallback tests.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest tests/test_export_model_fallback.py tests/test_export_fallback_files.py tests/test_export_remaining.py -q`

## Assumptions

- Optional fallback to `LLM_PROVIDER` is the compatibility choice in DEC-0089.

## Open Questions

- None.

## Activity Log

- 2026-11-07: Created and started with TASK-0274 and TASK-0275 on one branch. Owner accepted REQ-0090 and declined cross-language code.
- 2026-11-07: Slots are in the Python and TypeScript exporters. Python fallback tests and `test_export_remaining.py` passed. Deno is not installed here, so the TypeScript run was not executed.
- 2026-11-07: PR #336 CI is green at `b6c9e52b`, including Backend pytest, Postgres/Redis, Playwright, and factory verify (Deno runs there). Status stays doing until review and QA. Not merged.
- 2026-11-07: Review REV-0259 approved for QA. QA QA-0259 conditionally passed. Advisory only. Status stays doing. Not merged.
- 2026-11-07: Owner approved. Moved to done with Review REV-0259 and QA QA-0259. Not merged.

## Handoff Notes

- Owner approved on 2026-11-07. The task is done. Do not merge until the owner asks.
