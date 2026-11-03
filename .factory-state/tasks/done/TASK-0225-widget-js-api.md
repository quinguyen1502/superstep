# Task

## Metadata

- Project: superstep
- Task ID: TASK-0225
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-11-03
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0077, DEC-0079
- Phase: Phase 3 (PLAN-0002)
- Estimate: M (S up to half a day, M about one day, L two to three days)

## Objective

Give the widget a JS API, theming and signed-in embeds via token.

## Scope

### In Scope

- `window.Superstep`: `init`, `open`, `close`, `toggle`, `identify(token | getToken)`, `logout`, `on`/`off` (`ready`, `open`, `close`, `message`, `answer`, `error`), with a command queue for calls before load.
- Data attributes and init options for color, logo, language, position.
- The embed page accepts the token by `postMessage` only from the parent origin in `embed_origins`; never in the URL.
- Same API exposed on `/c/{slug}?embed=1` for the native bridge (TASK-0228).

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0077, DEC-0079.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0077, DEC-0079
- Review: `.factory-state/artifacts/REV-0220-task-0225-widget-api.md`
- QA: `.factory-state/artifacts/QA-0220-task-0225-widget-api.md`
- API contract: `docs/chat-widget-api.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)

## Expected Outputs

- The acceptance criteria below, tested.

## Constraints

- Layers of DEC-0009; common error envelope with codes in `core/errors.py` CATALOG, `docs/api-errors.md` and both locales.
- shadcn/ui and theme tokens only; en and vi keep the same keys; no emoji in docs.
- Schema changes through a new Alembic revision after the latest on `develop` at branch time.
- No secrets in logs, URLs or fixtures committed with real values.

## Dependencies

- TASK-0218
- TASK-0223

## Acceptance Criteria

- Playwright: a host page on another origin identifies a user, sees that user's history, logs out back to anonymous; events fire; a foreign origin's postMessage is ignored.

## Validation Plan

- `cd frontend && npm test && npm run test:e2e`
- Screenshots (en, vi, custom color)

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-11-03: Owner accepted PR #290 ("Duyệt") after e6b2f7c85b22eaae3d2428abb4f665ee5b0e4260 passed 21 CI checks with the expected GHCR publication skip. Move TASK-0225 to done on the same PR, record owner acceptance in REV/QA-0220, rebase on current develop 6218d840 and squash to one commit for Ready. Production/test/docs source is preserved; only lifecycle artifacts change. Required validation and checks apply to the rewritten head. Acceptance authorizes Ready finalisation; merging/publication still require explicit instructions.

- 2026-11-03: Implementation complete; advisory REV-0220 and QA-0220 pass. Move to review for one Draft PR. Full Factory profile 8/8 passes; canonical root build/lint/tests repeat successfully (frontend 157, React 18, TypeScript SDK 94). All 16 original targeted chat regressions pass, and the final widget/native acceptance suite passes 3/3. Screenshots en/vi/custom/dark visually inspected outside Git. Human acceptance remains pending; no move to done or release approval is inferred.

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0225-widget-js-api` from `develop`.

- 2026-11-03: Owner requested implementing the recommended TASK-0225 ("Ok tiến hành đi") through tests/screenshots and a separate Draft PR. Start from merged develop 6218d840; dependencies TASK-0218 and TASK-0223 are integrated. Preserve anonymous embeds and shared version 0.10.2; screenshots stay outside Git. No merge/release authority.

- 2026-11-03: factory ready exited 0 before implementation. task-start preparation is complete: clean integration base, accepted REQ-0082/DEC-0077/DEC-0079, merged dependencies and dedicated branch. Owner already requested full implementation, so continue through development/validation/review/QA without a second start confirmation. UX: existing bubble and iframe, programmable open/close, per-host theme/locale, signed-in user/history switching and logout to stored anonymous identity, typed-safe events. Origin/source checks and stale-identity cancellation are mandatory; tokens remain in memory and never URLs/events/logs.

- 2026-11-03: Implementation approach: retain one shared public-page layout for direct cookie visits and SDK-backed embeds; use the existing SDK hook for anonymous/app iframe transport, token refresh and cancellation, plus the existing cookie flow for studio-only signed-in embeds. Widget stays plain JS/DOM as DEC-0079 requires, with labels/palette generated from canonical frontend dictionaries/theme. JWTs and provider callbacks stay in memory; source+origin+document channel+identity epoch guard every bridge exchange. API/socket traffic originates at the Studio iframe, so widget keys must explicitly allow the Studio origin; embed_origins separately allowlists the parent. No claimed-parent-origin header or backend origin-policy exception. Native local frame API is prepared here; guides and platform bridge adapters remain TASK-0228. Primary postMessage reference: https://developer.mozilla.org/en-US/docs/Web/API/Window/postMessage (exact targetOrigin for sensitive messages; validate origin/source and shape).

- 2026-11-03: Browser acceptance exposed same-origin GETs omitting Origin. The API boundary now derives an origin only from an own/public-URL referrer with Sec-Fetch-Site: same-origin; explicit Origin wins, foreign referrers/cross-site/missing metadata still fail restricted keys. This is transport normalization, not a parent-origin claim or app-key allowlist bypass. Added positive/negative backend tests. Widget bundle uses ASCII output (classic scripts may inherit a legacy host encoding); dev script MIME explicitly declares UTF-8. Public API contract: docs/chat-widget-api.md.
- 2026-11-03: Initial acceptance passes 8/8 (new widget scenarios plus original anonymous/public embeds and direct public chats). New unit boundary suite passes 9/9 and React suite 18/18, including aborted implicit embed creation. Full final regressions/Factory verification and advisory review/QA are in progress; screenshot files are temporary only under /private/tmp/superstep-0225-visual/.
