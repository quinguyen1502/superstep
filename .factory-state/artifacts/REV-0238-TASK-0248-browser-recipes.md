# Review

## Metadata

- Project: superstep
- Review ID: REV-0238
- Task ID: TASK-0248
- Reviewer: Codex (self-review; owner review pending)
- Created: 2026-11-06
- Updated: 2026-11-06
- Outcome: scoped pass; declared verification passed

## Review Scope And References

TASK-0248 source 27cdf07d after task-start ac0f05f2, based on TASK-0247 #312 / REV-0237 / QA-0237 and TASK-0246 #311. ffff56cd carries predecessor status/evidence only. REQ-0086, DES-0004, ARCH-0002 recipe refinement, DEC-0085, PLAN-0006; `docs/browser-recipes.md`, example and Docker script. Full stack remains unmerged; owner approval pending.

## Findings

No blocking source finding after focused verification. A recipe is an ordinary bounded workflow, not a second store/runtime/model loop. Strict v1 metadata limits it to a fixed connection and linear 1–20 shared browser actions, closed primitive inputs and declared bounded object outputs. Exact role/text matches over earlier bounded observations reject ambiguous/missing layouts. Worker references/fingerprints remain authoritative. Compiler derives shared-group markers and strips supplied ones. Default effect approval, profile/proxy/origin/fence checks remain unchanged.

Resolved review findings: parent-only fork guards could miss a browser in a workflow-tool child, and a parent model could create a new recipe child after an uncertain previous child. Recursive SQLAlchemy history now covers descendants and refuses those retries. Existing child-key lookup can report an old result but never replaces its page. A recipe queued before a save must retain its accepted definition even if a process dies before first progress; queue snapshots and recovery now preserve it. Recipe rejection remains explicit in the parent error, rather than collapsing to a generic failed-before-effect message.

Existing workflow ownership/token/PAT/rate rules control discovery/invocation. Agent snapshots and MCP queue acceptance preserve definition/revision. Actual MCP SDK tests show that token/model resume text has no Human receipt and cannot grant fill/click. Reading completed results sends no new browser action.

## Standards And Design Alignment

Engine contracts/selectors use existing state templates; services own access/lifecycle, repositories use SQLAlchemy including a bounded recursive CTE. No new schema/dependency/endpoint. New error code is in the core catalog, API docs and both error/validation locales with one English source. Recipes reuse workflow deletion and its shared exact-name confirmation. No new UI component; connection/recipe/trace UI and accessibility acceptance remain TASK-0249/0250. Runtime stays experimental/default off; exports remain TASK-0251/0252.

## Validation Review

Broad recipe/session/child/approval/workflow/MCP/effect/envelope/layer/locale regressions: 112 passed, 3 optional skips before final snapshot/rejection additions. Later recipe/restart/layer: 29 passed, 1 optional skip; final recipe/envelope/layers/locale: 37 passed, 1 optional skip. Disposable SQLite/PostgreSQL migration/CAS/recursive-history suite: 10 passed. Actual Chromium recipe fixture passed final precommit source (same bytes as 27cdf07d): two URLs/IDs, six actions and two Human approvals per call, declared-only output, layout stop, injected lost acknowledgment, three intended POSTs and zero repeats. No screenshots committed. Full eight-command profile is running on committed source.

## Limits And Follow-Up

Role-only extraction needs one unique reviewed semantic role; it does not attest business meaning. Effects after dispatch may be unknown and cannot be undone; no exactly-once promise. Definitions cannot exceed smaller connection/runtime limits or increase authority. Recipe UI/selectors remain JSON/API until assigned UI tasks. Live provider/profile/deployment and export acceptance are not claimed. Review final full checks and locale wording against the glossary before publication.

## Review Decision

Conditionally approved for scoped QA with declared verification and locale wording checks passed; owner approval pending. No done/Ready/merge approval.

- Final canonical full profile on 27cdf07d (only documentation followed during the run): all eight commands passed. Backend 483.94 s; root build/lint/test 11.83/1.16/16.65 s; Python SDK 14.76 s; TS SDK build/test/typecheck 1.58/1.46/1.46 s. A subsequent wording-only vi correction uses the input/output glossary; root npm test passed 280 tests and backend locale/envelope passed 14 tests (5.60 s). No backend behavior/source changed after the full profile. Owner review remains pending; no done/Ready/merge approval.
