# Review

## Metadata

- Project: superstep
- Review ID: REV-0223
- Task ID: TASK-0230
- Reviewer: Codex (advisory)
- Created/Updated: 2026-11-03
- Outcome: no blocking findings; local verification and source CI pass; final metadata-head CI gates delivery

## Review Scope

Diff against merged develop 42333ffc (#292/TASK-0229): latest-terminal-answer regeneration through the existing independent branch/intent/file/stream pipeline, source_action lineage (Alembic 0054), public/Studio endpoints and additive capabilities/turn flags, TS/Python helpers, shared React/Studio/public/widget controls, en/vi docs and acceptance. No native work or version/publication change.

## Reference Artifacts

TASK-0230; REQ-0082; PLAN-0002; accepted DEC-0084; DEC-0008/0009/0010/0077/0078/0079; docs/ui-conventions.md and docs/backend-architecture.md; QA-0223. Foundation review/QA: REV-0222/QA-0222.

## Findings

### Blocking

No unresolved blocking source finding. Review checked:

- Only the last terminal, owned, non-inherited assistant turn can select its initiating root; older answers, root/Human turns and inherited prefix are refused. Waiting/running/pending-source checks and revision CAS remain shared. The root and prefix are chosen on the server; input/state/checkpoint fields are not accepted.
- Regeneration excludes the prior attempt's Human/reviewer responses, uses a new reserved run ID and ordinary execution/approvals, and preserves source turns/ratings. Independent file staging, current policy checks, compensation and durable once-only claim are reused rather than reimplemented.
- Regeneration fingerprints are disjoint from legacy edit payloads, while old edit fingerprints remain valid. Reusing one operation ID across actions conflicts, including a payload crafted to mimic the other action's identity.
- Repeated admitted intents after later branch messages formerly skipped their own saved answer. A before-fix SDK regression fails for edit and regenerate; recovery now starts before the reserved run and does no socket write. TypeScript store state retains a later Human wait. Python sync/async cover the continued-branch case too.
- One shared confirmation renders edit or regenerate; only the latest answer offers the latter, including errors/cancellations. The UI also guards against stale earlier capability flags in incrementally loaded history.

### Non-Blocking

A claimed but unsaved run remains unknown/non-replayable after process loss, as accepted in DEC-0084. Copies consume storage and the current workflow can repeat external effects; the shared warning remains explicit. Historical agent metadata may expire. These limitations remain documented, not replaced by checkpoint or model-only semantics.

## Standards And Architecture Alignment

Routers call services, repositories retain transaction ownership, no FastAPI enters services and no raw SQL is added. Alembic 0054 adds one nullable lineage-action column; old branches infer edit. New error codes are in the shared catalogue, error guide, both locales and SDK mappings. Existing edit HTTP/socket shapes and response schema names stay compatible; regenerate reuses the existing edit_operation_id admission field. Public ownership/origin/revocation/quota checks are unchanged.

The DEC-0008 checklist passes: existing shadcn modal/buttons/alerts and semantic tokens, labelled latest-answer action, en/vi parity/glossary, ordinary size variants and existing typed-name deletion. No new delete/template/node-config fields. Light Studio, dark public/widget and custom-theme React captures were inspected outside Git with no clipping or action alignment defect.

## Design Alignment

Accepted DEC-0084 is followed: new branch from the initiating root's prefix, current saved/published workflow, fresh Human/reviewer approvals, original navigation, readonly inherited feedback/files with independent ownership, stable operation IDs across unchanged retries and no external-action replay on recovery. Shared UI/SDK transports avoid per-channel implementations.

## Validation Review

See QA-0223 for targeted/API/SDK/browser/handbook evidence. The first full profile passed seven commands and all backend behaviour tests, with only a stale generated AsyncAPI description; canonical regeneration and 25 contract checks pass. Full profile reruns in superstep-0230-verify-final.log; exact pushed-head SQLite/Postgres/MinIO and complete E2E CI must pass before owner acceptance/merge.

## Assumptions

Synthetic models/accounts only; no real vendor/customer data. Shared Python/CLI/server version stays 0.10.2 until the separately gated 0.11.0 release preparation.

## Required Follow-Up

Complete the full profile and exact-head CI, keep one Draft implementation PR/task in review for owner acceptance, then integrate before release preparation. Do not infer merge/tag/publication permission for this new PR from approval of #292.

## Review Decision

Advisory source review approved for QA; no blocking findings. Final verification/CI and owner implementation acceptance remain delivery gates.

## Final Validation Review (2026-11-03)

Final local profile passes all eight commands and canonical report records passed. Source head f0474eb7 on PR #293 passes all 22 CI checks (two expected skips), including 55 live MinIO tests, PostgreSQL/Redis, all E2E shards and React 18/19. Full source/API/SDK/browser acceptance has no outstanding failure. Finalisation changes records only, including correction of an accidentally committed stale failed verification snapshot. Owner implementation/merge approval and exact final-head checks remain required; the PR stays Draft. This supersedes earlier pending-local-validation statements.

## Owner Implementation And Merge Acceptance (2026-11-03)

Owner explicitly instructed "Merge" on PR #293. Reviewed head 922ea6a840ba68b4fa47450d3e18993ba8ae4a74 passes all 22 checks with two expected deploy/publication skips: CI run 41654796986, Factory verification 41654797066, handbook 41654797008, image 41654797094 and CLI 41654797495. Local full verification passes 8/8. No unresolved blocking finding or QA failure remains. This supersedes earlier pending-owner statements. The move to done is on this same PR in its one task commit, based on latest develop 42333ffc. Finalisation changes records only; source validation is reused and exact final-head CI must pass before the owner-authorised merge. Release preparation follows integration; no release tag, registry publication or native completion is inferred.
