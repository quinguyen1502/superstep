# Review

## Metadata

- Project: superstep
- Review ID: REV-0208
- Task ID: TASK-0231
- Reviewer: Codex self-review (advisory; owner review pending)
- Created: 2026-11-01
- Updated: 2026-11-01
- Outcome: approved for QA

## Review Scope

Reviewed the diff from origin/develop: planning baseline for REQ-0083 and opt-in LLM model fallback, validation, runtime attempts, template sanitisation, explicit export refusal, editor configuration, tests and bilingual documentation.

## Reference Artifacts

- REQ-0083, DES-0001, DEC-0081, PLAN-0003, TASK-0231.
- docs/backend-architecture.md and docs/ui-conventions.md.

## Findings

### Blocking

- No blocking findings.

### Non-Blocking

- Configured fallback currently refuses Python/TypeScript export explicitly. This is an accepted task boundary, exposed in UI, handbook and a translated catalogue error.
- Successful-attempt usage is recorded; a failed provider may still charge for work for which no usage response was received. No zero-cost guarantee is made.
- A node retry repeats the whole two-model policy. This is documented; authentication, credential permission and cancellation do not cause failover.

## Standards And Architecture Alignment

Engine policy has no service/API dependency; credentials use the existing owner-bound resolver. Alternate credentials resolve before any paid call. Metadata excludes credential ids and secrets. Failed-primary output is buffered; ordinary nodes retain streaming. Shared errors/i18n and Settings tab conventions followed. No schema change, dependency or delete feature added.

## Design Alignment

Existing ModelPicker, shadcn controls, labels, read-only fieldset and theme tokens; en/vi keys match. Alignment and persistence are covered by browser tests. No new graph node type.

## Validation Review

Focused backend suite: 57 passed. Frontend unit suite: 149 passed. Full Factory verification passed all eight checks; final small Select controlled-value fix was followed by frontend build/lint and browser checks. Handbook builds and image validation passed. See QA-0208 for final browser evidence.

## Assumptions

- Owner authorised implementation and Draft PR delivery; approval to merge is pending.

## Required Follow-Up

- Owner review on the same task PR. Continue TASK-0232–0234 on explicitly documented stacked branches.

## Review Decision

Approved for QA, advisory only; no owner approval inferred.
