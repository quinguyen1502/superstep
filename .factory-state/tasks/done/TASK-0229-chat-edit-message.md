# Task

## Metadata

- Project: superstep
- Task ID: TASK-0229
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-11-03
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0084 (Accepted)
- Phase: 0.11.0 priority; architecture accepted (PLAN-0002)
- Estimate: L (S up to half a day, M about one day, L two to three days)

## Objective

Deliver non-destructive sent-message editing through the shared chat stack for 0.11.0, after approval of DEC-0084.

## Scope

### In Scope

- Accepted DEC-0084 shared branch/admission foundation; edit operation; Studio/public v1 contracts, TypeScript/Python helpers and shared React/public/widget UI; file lifecycle, deduplication, en/vi docs and acceptance tests. Regenerate remains TASK-0230.

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, accepted DEC-0084.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: `.factory-state/decisions/DEC-0084-chat-edit-regenerate.md` (Accepted on 2026-11-03)
- Review: `.factory-state/artifacts/REV-0222-task-0229-chat-edit.md`
- QA: `.factory-state/artifacts/QA-0222-task-0229-chat-edit.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)

## Expected Outputs

- The acceptance criteria below, tested.

## Constraints

- Layers of DEC-0009; common error envelope with codes in `core/errors.py` CATALOG, `docs/api-errors.md` and both locales.
- shadcn/ui and theme tokens only; en and vi keep the same keys; no emoji in docs.
- Schema changes through a new Alembic revision after the latest on `develop` at branch time.
- No secrets in logs, URLs or fixtures committed with real values.

## Dependencies

- TASK-0216

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

- Branch `factory/task-0229-chat-edit-message` from `develop`.

- 2026-11-03: Owner accepted DEC-0084 on PR #292 ("Approve") and authorised implementation. Preserve versions until release preparation and screenshots outside Git. No merge authority is implied.

- 2026-11-03: factory ready exits 0 before source work. Existing branch/PR #292 is based on develop 02361fbd. Implement shared branch/admission and edit through existing layers; DEC-0084 is accepted.

- Implementation: Alembic 0053; independent history/files; source-version CAS and durable intent claim; Studio/public v1 preparation followed by ordinary chat streaming; TypeScript/Python helpers; shared React/Studio/cookie/embed editing and typed-name session removal. New staged resources use full UUIDs. Inherited turns remain read-only.
- Regression review: corrected historical agent resets after target removal/readdition, and an older pending root hidden by a later completed answer. Both have before-fix reproductions and passing regressions. Missing required historical agent metadata fails closed; no state/checkpoint API is exposed publicly.
- Final local regression set: 16 passed / 1 MinIO-only skip, including explicit quota denial, concurrency/deduplication, app identity/origin/key rotation, file policy/cleanup and source preservation. Studio/cookie-public browser editing passes in en/vi; host React 18/19 matrices cover toolkit/widget/headless plus Human/files/identity. Final full profile runs in /private/tmp/superstep-0229-verify-final.log; the preceding run passed seven commands but functional public fixtures inherited shared IP budget, now isolated without changing quota assertions.
- Screenshots are ignored test output and /private/tmp/superstep-0229-visual; no images/auth traces are added to Git. Owner accepted DEC-0084, not the new software delivery or merge. TASK-0230 follows the merged shared foundation; native work remains deferred.
- 2026-11-03: Final full Factory profile passes 8/8 commands; final React tests pass 19/19; strict en/vi handbook and image validation pass. Final React 18/19 host runs each pass all three Node tests plus toolkit/widget/headless browser scenarios, including no inherited widget events. Advisory review REV-0222 has no blocking findings; QA-0222 passes local acceptance. Enter review on existing Draft #292; exact pushed-head CI (including live MinIO) and owner software approval remain delivery gates. Final UI fallback was built/tested after the full profile and covered by both final host runs.

- 2026-11-03: Owner explicitly approved merging #292 and continuing TASK-0230 ("Approve" after the merge request). Reviewed head b80a0a1a passed 22 CI checks with two expected deploy/publication skips: SQLite 1221 passed/26 skipped, PostgreSQL/Redis 1187 passed/60 skipped, live MinIO 46 passed; all full E2E shards and React 18/19 host matrices passed. Move to done on this same PR, squash to one commit against latest develop, verify unchanged source, run final validation and wait for final-head CI before the authorised merge. No release tag/publication is authorised.
