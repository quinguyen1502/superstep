# Review

## Metadata

- Project: superstep
- Review ID: REV-0222
- Task ID: TASK-0229
- Reviewer: Codex (advisory; owner implementation acceptance remains separate)
- Created/Updated: 2026-11-03
- Outcome: no blocking findings; local verification passed; pushed-head CI gates delivery

## Review Scope

Diff against develop 02361fbd: accepted DEC-0084 and release-priority amendment, Alembic 0053/session revision metadata/durable edit intents, shared chat admission and independent history/file copies, Studio/public v1 endpoints and additive socket field, TypeScript/Python helpers and recovery, shared React/Studio/public/widget editing, typed-name session deletion, en/vi guides and tests. TASK-0230 regeneration and native implementation are excluded. Versions and dependencies remain unchanged.

## Reference Artifacts

REQ-0082, PLAN-0002, accepted DEC-0084; DEC-0008/0009/0010/0057/0077/0078/0079; docs/ui-conventions.md; docs/backend-architecture.md; TASK-0229; QA-0222.

## Findings

### Blocking

No unresolved blocking source finding. The full local profile passed; exact-head CI still gates delivery. Review resolved these issues before handoff:

- Prefix routing must use the latest retained run's actual start input and successful handoff, including a reset when a target was removed. Scanning back to an older handoff incorrectly restored Billing after reset; an API-level regression reproduces the failure and now passes. Missing required historical agent context refuses the operation instead of guessing.
- A later completed answer cannot hide an earlier pending chat message. Admission checks all root outcomes and active associated runs, as well as the source version CAS. A regression reproduces the former admission and now verifies CHAT_EDIT_BUSY.
- Concurrent preparation of one intent returns the winning record after a failed source CAS; only one durable execution claim succeeds. The original root/answer/ratings are untouched.
- Staged IDs use full UUIDs, with an ordering prefix only on copied turn IDs. Copied attachment keys match the existing service-key format, preserving orphan cleanup. Files are independently owned; late source changes clean staged rows/objects.

### Non-Blocking

- Preparation and execution are separate. A process lost after claiming but before saving its run remains non-replayable; bounded recovery can report interruption. No automatic retry of external actions is inferred. The API guide states this limitation.
- Copies consume extra storage; retained prefix ratings are not copied into feedback totals. Historical agent context that has expired may prevent an old fork while leaving its text readable.
- Current saved/published workflow execution can repeat deliberate external effects. The UI explicitly confirms that behaviour; existing Human/reviewer approvals still apply. No rollback or model-only rewrite is claimed.

## Standards And Architecture Alignment

Routers call services; repositories own SQLAlchemy transactions; services import no FastAPI. Schema changes have an Alembic revision. Responses use the shared envelope; new catalogue codes have API documentation, en/vi strings and SDK mappings. Existing v1 messages/answers remain valid; new capabilities/lineage/readonly fields and the edit operation field are additive. Public ownership, origin, key revocation and quota checks remain in their existing boundaries. No caller-supplied state, workflow, owner or checkpoint is accepted.

The shared shadcn presentation owns the edit modal and actions. New copy is canonical en/vi; warning styling uses theme tokens. Session removal now uses the shared typed-name dialog, with display whitespace normalised for multiline titles; the API stays plain DELETE. Screenshots remain ignored/temp outputs, never repository assets.

The DEC-0008 UI checklist passes: shared shadcn controls, theme tokens, semantic warning/error icons, matching en/vi keys and glossary, ordinary size variants and typed-name deletion. No node fields or template controls are introduced. Light Studio, custom-theme React and dark en/vi widget captures were inspected; no clipping or misaligned actions were found.

## Design Alignment

Edit/save/cancel preserves the original, selects the branch and offers an original-conversation action, including an empty prepared branch. Human response turns and inherited history cannot be edited. Inherited feedback is read-only in shared and composed components and on the server. One intent ID is retained across unchanged dialog retries. Widget events exclude inherited history and retain identity-epoch isolation. Root files are copied, remapped and checked against current limits before execution.

## Validation Review

See QA-0222 for current checks and exact-head CI on #292. Initial failures included test selectors that also included file labels, a persisted widget locale assumption, and shared functional-test IP budgets. These fixtures were corrected without weakening file, identity, quota or duplicate-execution assertions. Actual routing/pending-run defects have explicit before-fix reproductions and passing regressions.

## Assumptions

Internal operator-controlled workflows/storage; synthetic model/provider fixtures. Public v1 compatibility and independent npm versus shared Python/CLI/server versioning are retained.

## Required Follow-Up

Declared verification passed all eight commands. Complete exact-head MinIO/SQLite/Postgres/browser CI; its result is recorded on existing PR #292. Keep this same PR Draft for implementation review; TASK-0230 follows its merged foundation. Do not merge, tag or publish from architecture acceptance alone.

## Review Decision

Recommended for owner review (advisory): no blocking findings, local verification and QA pass. Pushed-head CI and owner approval of the implementation remain required.

## Owner Acceptance And Finalisation (2026-11-03)

Owner explicitly approved implementation/merge of #292 and continuing TASK-0230 ("Approve"). Reviewed source head b80a0a1a passes all 22 CI checks with two expected deploy/publication skips, including live MinIO (46 passed), SQLite (1221 passed/26 skipped), PostgreSQL/Redis (1187 passed/60 skipped), all three E2E shards and React 18/19 host matrices. No unresolved blocking finding or QA failure remains. Finalisation changes lifecycle records only; final single-commit checks must pass before the authorised merge. This supersedes the earlier pending-owner/CI statements. No native completion, release tag or package publication is implied.
