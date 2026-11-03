# Task

## Metadata

- Project: superstep
- Task ID: TASK-0230
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-11-03
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0084 (Accepted)
- Phase: 0.11.0 priority; architecture accepted (PLAN-0002)
- Estimate: M (S up to half a day, M about one day, L two to three days)

## Objective

Deliver regeneration of the latest terminal answer through the shared branch foundation for 0.11.0, after approval of DEC-0084.

## Scope

### In Scope

- Accepted DEC-0084: rerun the latest terminal answer's root in an independent branch through TASK-0229's merged foundation; preserve the original and confirm that the current workflow can repeat external effects. Reuse shared APIs, SDKs and UI; no checkpoint restore or replacement of the source answer.

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, accepted DEC-0084.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: `.factory-state/decisions/DEC-0084-chat-edit-regenerate.md` (Accepted on 2026-11-03)
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)

## Expected Outputs

- The acceptance criteria below, tested.

## Constraints

- Layers of DEC-0009; common error envelope with codes in `core/errors.py` CATALOG, `docs/api-errors.md` and both locales.
- shadcn/ui and theme tokens only; en and vi keep the same keys; no emoji in docs.
- Schema changes through a new Alembic revision after the latest on `develop` at branch time.
- No secrets in logs, URLs or fixtures committed with real values.

## Dependencies

- TASK-0229 (shared branch foundation must be merged first)

## Acceptance Criteria

- DEC-0084 Acceptance And Validation: source history remains unchanged, branch ownership/admission is atomic and deduplicated, inherited files/ratings remain safe, shared clients/UI and en/vi docs support the action.
- Focused functional/security/failure/concurrency tests and browser acceptance pass; screenshots stay outside Git.

## Validation Plan

- DEC-0084 acceptance matrix; full Factory verification; public schema/SDK checks; existing Studio/public and cross-origin React 18/19 browser jobs; strict en/vi handbook build.

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-11-03: Owner explicitly prioritised TASK-0229/0230 for version 0.11.0 and temporarily deferred TASK-0227/0228. Proposed shared DEC-0084 defines branch/rerun semantics and acceptance. Priority/release target is authorised; the new architecture remains Proposed. No source work or version bump before decision acceptance. TASK-0229 carries this shared planning change on its branch; TASK-0230 keeps a separate implementation PR after the foundation merges.

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0230-chat-regenerate-answer` from `develop`.

- 2026-11-03: Owner accepted DEC-0084 on PR #292 ("Duyệt") and authorised implementation. Preserve versions until release preparation and screenshots outside Git. No merge authority is implied.
