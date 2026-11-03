# Review

## Metadata

- Project: superstep
- Review ID: REV-0209
- Task ID: TASK-0232
- Reviewer: Codex self-review (advisory; owner review pending)
- Created: 2026-11-01
- Updated: 2026-11-01
- Outcome: approved for QA

## Review Scope

Own diff from factory/task-0231-model-fallback (33af7c6, Draft PR #278): event policy in existing trigger settings, shared envelope/admission/mapping, Telegram metadata, signed JSON channel, atomic event/run insertion and queue retry recovery, translated trigger UI and handbook.

## Reference Artifacts

- REQ-0083, DES-0001, DEC-0081, PLAN-0003, TASK-0232.
- docs/backend-architecture.md and docs/ui-conventions.md.

## Findings

### Blocking

- No blocking implementation findings. Final full profile must pass before Ready/completion; Draft PR may carry the pending check.

### Non-Blocking

- One event binding per connection/place; existing command bindings have priority. Delivery IDs are unique within a connection, not only within a binding. Documented behavior.
- Event mode intentionally runs with the trigger creator's resources after explicit sender admission and SHARE/RUN checks. It sends no implicit processing/success replies; managed tools are the next task.
- Wrong admission/type/mapping is ignored without creating runs. Callback rate limits remain the admission rate guard.

## Standards And Architecture Alignment

Routers use services and shared envelope. SQLAlchemy transactions live in the repository. Reuses existing JSON columns, so no schema migration is needed. Signing secrets use existing encrypted channel storage. Webhook source cannot be used for approvals/account linking. No arbitrary evaluation, URLs or secret workflow fields. At most one run is inserted concurrently; queue redelivery uses persisted original input.

## Design Alignment

Existing trigger dialog, shadcn components/theme tokens, labels, two locales and shared typed-name deletion retained. Browser tests cover creation/edit/toggle/delete and signed input. Header now states event owner authority explicitly; ordinary commands keep the old description.

## Validation Review

Initial focused backend 47 passed; final eight event cases passed, including revoked organisation policy. Frontend build/lint and 149 unit tests passed; final browser suite five passed in 26.1 s. Both handbook builds and media check passed. Full profile passed all eight checks on isolated source commit 6b9657b (see QA-0209).

## Assumptions

- Stacking is authorised by PLAN-0003, not approval to merge. No production bot registration or real external messages.

## Required Follow-Up

- Complete final verification and owner review. Continue TASK-0233/0234 on documented stacked branches.

## Review Decision

Approved for QA; final verification passed, advisory only. Owner approval pending on #279.

## Landing Approval

Owner approved implementation and merge of #279 on 2026-11-02. All screenshot evidence is intentionally removed at the owner's request; the historical validation results above remain recorded. Final rebased/squashed head must pass required integration checks before merging.
