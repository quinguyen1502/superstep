# Task

## Metadata

- Project: superstep
- Task ID: TASK-0226
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-11-03
- Requirement IDs: REQ-0082
- Design IDs: none
- Architecture IDs: DEC-0079
- Phase: Phase 3 (PLAN-0002)
- Estimate: S (S up to half a day, M about one day, L two to three days)

## Objective

Document the web toolkit and widget API (en, vi), and add the React toolkit to the sample host e2e.

## Scope

### In Scope

- Handbook `run/chat-react.md` and `run/chat-widget.md` (en, vi); package READMEs; CHANGELOG.
- Extend `examples/chat-host` with a React page and a widget page, covered by the e2e job.

### Out Of Scope

- Anything assigned to another task in PLAN-0002.

## Inputs

- REQ-0082, PLAN-0002, DEC-0079.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0082-chat-sdk-toolkit.md`
- Plan: `.factory-state/artifacts/PLAN-0002-chat-sdk-toolkit.md`
- Architecture: DEC-0079
- Review: `.factory-state/artifacts/REV-0221-task-0226-web-docs-examples.md`
- QA: `.factory-state/artifacts/QA-0221-task-0226-web-docs-examples.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)

## Expected Outputs

- The acceptance criteria below, tested.

## Constraints

- Layers of DEC-0009; common error envelope with codes in `core/errors.py` CATALOG, `docs/api-errors.md` and both locales.
- shadcn/ui and theme tokens only; en and vi keep the same keys; no emoji in docs.
- Schema changes through a new Alembic revision after the latest on `develop` at branch time.
- No secrets in logs, URLs or fixtures committed with real values.

## Dependencies

- TASK-0224
- TASK-0225

## Acceptance Criteria

- Handbook build passes; the e2e job covers both pages.

## Validation Plan

- CI `chat-host-e2e` job
- handbook build

## Assumptions

- The owner accepts REQ-0082 and DEC-0077 to DEC-0080 (or their amended versions) before this task moves to todo.

## Open Questions

- See PLAN-0002 and the related DECs.

## Activity Log

- 2026-11-03: Owner accepted PR #291 ("Approve") after head 5d2d847131051ce951a3bcaf9267160036dcd07a passed 22 CI checks with two expected deployment/publication skips. Move TASK-0226 to done on this same PR, record acceptance in REV/QA-0221, rebase on latest develop 2ea51b0a and squash into one commit for Ready. All implementation/docs/tests are preserved; only lifecycle artifacts change. Required checks apply to the rewritten head. This acceptance does not authorise merge or release.

- 2026-11-03: Source review REV-0221 and local QA-0221 pass. Full Factory rerun 8/8, final root tests (157 frontend / 18 React / 94 TypeScript SDK), strict en/vi handbook/media checks and both React 18/19 sample matrices pass. Node security/static and React/widget/headless browser scenarios pass. Initial backend environment failures and Human-turn/screenshot fixture corrections are documented in QA; no production assertion was weakened. Move to review for one Draft PR; owner acceptance remains pending. Screenshots stay outside Git.

- 2026-10-31: proposed in PLAN-0002 from REQ-0082. Status backlog until the owner approves the plan.

## Handoff Notes

- Branch `factory/task-0226-web-toolkit-docs-examples` from `develop`.


- 2026-11-03: Owner requested merging #290 and proceeding with the next task. #290 merged as 2ea51b0ab424a53a3ec6ce92e572d130a8adc48a after all 21 checks passed; #289 is already merged. TASK-0226 is the next phase-3 task per PLAN-0002; no active lifecycle task takes priority. Owner authorizes implementation, bilingual docs/examples, validation/screenshots outside Git and one Draft PR. Preserve shared Python/CLI/server 0.10.2 and existing npm versions. Start preparation does not require a second confirmation; no merge/publication authority for the new PR is inferred.

- 2026-11-03: factory ready exited 0 before source work. Task-start preparation is complete on factory/task-0226-web-toolkit-docs-examples from merged develop 2ea51b0a. Goal: bilingual React/widget handbook pages and discoverable, runnable sample pages covered by chat-host-e2e. Reuse the existing React toolkit example, shared session/token server and canonical translations/shadcn components; add the plain-JS widget sample without duplicating transport or authentication. Acceptance: strict en/vi handbook builds and browser coverage for both samples; screenshots stay outside Git. Continue through implementation and a Draft PR under the owner's instruction to proceed.

- 2026-11-03: Implementation reuses the existing React example at /react/ and adds /widget.html to the shared headless portal shell (shadcn controls/canonical translations). All three pages use the existing opaque HttpOnly demo session and server-only signer. The widget remains the Studio's plain-JS script; the demo host shell's React does not become a widget dependency. Static routes preserve path containment/no-store and restrict CSP script/frame origins to the configured Studio. No new auth endpoint or client-side secret.
- 2026-11-03: chat-host-e2e now builds/serves the actual Studio on its isolated API, seeds the parent embed allowlist plus explicit Studio/host key origins, then tests React, widget and headless in order; terminal key revocation stays last. Both React 18/19 matrix runs pass all three browser scenarios and three Node security/static tests. New widget acceptance checks anonymous/app history, two personas, Human answer turns/events, server-issued auth, logout restoration and cross-page session reuse. Initial fixture expected one message event, but a Human answer persists a second user turn; corrected to the documented persisted-turn semantics without changing production code. Final wording-only count labels and metadata checks remain to verify.
- 2026-11-03: Added en/vi React/widget guides, navigation/cross-links, package/sample READMEs and Unreleased changelog. Strict handbook builds and image check pass before final copy review. Screenshots are ignored/temp files, never committed. Factory full verification, advisory source review/QA and one Draft PR are next; whole REQ-0082/native tasks and publishing are not claimed complete.

- 2026-11-03: Final-head Factory CI exposed shared rate-limit state in test_page_loads_are_limited_per_ip. Reopen this same task for a minimal test-isolation correction, then repeat validation and single-commit Ready finalisation. Production code and rate-limit assertions remain unchanged.

- 2026-11-03: Rate-limit isolation correction passes with deliberately exhausted shared quota (all nine public-chat tests), then full Factory verification passes 8/8 (backend 484.46s, Python SDK 14.16s). Restore done on the same approved PR and squash the correction into its single task commit; exact-head CI must pass before Ready. Product implementation/docs/versions remain identical to the owner-reviewed head.
