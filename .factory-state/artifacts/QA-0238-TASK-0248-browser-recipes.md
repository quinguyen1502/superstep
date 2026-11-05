# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0238
- Task ID: TASK-0248
- QA Owner: Codex (advisory; owner approval pending)
- Created: 2026-11-06
- Updated: 2026-11-06
- Outcome: scoped conditional pass; full declared verification pending

## Scope And References

REQ-0086, DES-0004, ARCH-0002 recipe refinement, DEC-0085, PLAN-0006, REV-0238, `docs/browser-recipes.md` and `examples/browser/lookup_shipment.json`. Source 27cdf07d; explicit unmerged stack on TASK-0247 #312 and TASK-0246 #311.

## Acceptance Criteria Coverage

- lookup_shipment(url, order_id): passed actual isolated Chromium for two different per-call URLs/IDs, six shared-page actions and two approvals per call. Final output contains only declared shipment extraction, no intermediate page/input fields.
- Shared handlers/policy and generic invocation: passed production RunService binding, existing Agent workflow child slot and actual MCP SDK/server. Discovery exposes a closed typed schema; invalid extras reject before queueing. Model/token resume cannot grant a Human browser receipt. Same connection/fence/page/receipt and terminal cleanup handlers are used; no second model call/Agent fallback inside the recipe.
- Bounds/access/versions/layout: passed strict integer v1, required/bounded primitive inputs, unknown authority args, sequence/type/connection/retry constraints, missing/ambiguous target and existing workflow authorization. Parent and API/MCP accepted snapshots remain stable after saving a changed definition, including recovery before first progress.
- No replay after missing/unknown page: passed real POST followed by lost ack, unknown result and no replacement/repeat; descendant history blocks parent fork/new-child retry. Completed MCP result reads send no additional actions. Existing workflow typed-name deletion is reused, with no new delete API.

## Checks Performed

- Recipe/session/child/approval/workflow/MCP/effect/envelope/layer/locale regressions: 112 passed, 3 optional skips before final snapshot/rejection additions (37.14 s).
- Recipe/restart/layer after snapshot recovery: 29 passed, 1 optional skip (65.08 s).
- Final recipe/envelope/layers/locale after explicit rejection: 37 passed, 1 optional PostgreSQL skip (9.16 s).
- Disposable PostgreSQL 17 + SQLite migrations/process CAS/recursive child history: 10 passed (20.10 s); fixture/data removed.
- Final actual `scripts/test-browser-recipes.py --skip-build`: passed two calls with different URL/ID, two approvals/six actions each, declared-only output, changed-layout stop, lost-ack unknown, exactly three intended POSTs and zero repeated effects. Resources close before temporary DB removal; screenshots written to Git: 0.
- Factory ready passed before source. Generated contract check, compile/whitespace passed; full eight-command Factory profile running on committed 27cdf07d.

## UX And Accessibility Coverage

No UI component changed. Error and validation locales exist and parity checks pass; final glossary wording review pending. Recipe connection/selector builder controls and full keyboard/narrow/theme/locale acceptance remain TASK-0249/0250. Workflow deletion continues through the existing shared exact-name dialog and plain DELETE API.

## Gaps, Risks And Required Follow-Up

Full declared verification and final locale wording review pending. Backend-only recipe metadata is not a finished UI/export claim. Unique semantic role/text must reflect the reviewed site; business meaning/layout cannot be inferred by an Agent inside the recipe. Unknown external effects stop conservatively, with no undo/exactly-once promise. Live account/provider configuration and remote recipe-specific fixture are not claimed (remote/shared six-action primitives were verified in prerequisite tasks). Runtime defaults off.

## QA Decision

Conditionally passed for scoped review pending final checks/locale wording and owner approval. No done/Ready/merge authority.
