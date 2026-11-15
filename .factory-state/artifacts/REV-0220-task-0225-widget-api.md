# Review

## Metadata

- Project: superstep
- Review ID: REV-0220
- Task ID: TASK-0225
- Reviewer: Codex (advisory source review; owner approval remains separate)
- Created: 2026-11-03
- Updated: 2026-11-03
- Outcome: owner accepted; approved for Ready finalisation

## Review Scope

Diff from develop 6218d840: plain-DOM widget API/queue/theme, checked iframe bridge, shared published-page layout, SDK-backed anonymous/app embeds, retained cookie visits, minimal React composition/embed options, canonical generated labels/palette, API origin normalization, tests and docs/chat-widget-api.md. No schema, package version, release, deployment or framework asset change.

## Reference Artifacts

- TASK-0225, REQ-0082, PLAN-0002.
- DEC-0077-chat-third-party-auth.md, DEC-0079-chat-packages-ui-reuse.md.
- docs/ui-conventions.md, docs/backend-architecture.md, docs/chat-widget-api.md.

## Findings

### Blocking

No unresolved blocking source findings. Final verification evidence is recorded in QA-0220; owner acceptance remains pending.

Resolved during development: same-origin browser GETs omit Origin; restricted keys now accept only an own/public-URL referrer with same-origin Fetch Metadata. Explicit Origin wins; foreign referrers, cross-site/missing metadata and foreign key origins remain rejected. No caller-supplied parent-origin override or relaxed key policy. Classic-script output is ASCII so a host's legacy encoding cannot corrupt Vietnamese labels.

Identity transitions clear the old controller before awaiting providers. Every bridge exchange checks the exact window, origin, document nonce and epoch. Stale provider completions, refresh replies and active work cannot repopulate a different person's history/events. StrictMode replay preserves the live bridge and restores the prior global only on a real unmount. JWTs/providers remain private memory; only structurally validated visitor HMACs enter storage. Event payloads explicitly pick safe turn fields. History replay does not emit new-turn events.

### Non-Blocking

- The widget's app-key origin is Studio's iframe origin; embed_origins separately controls the parent site. Both are documented and exercised positively/negatively.
- Browser coverage is desktop Chrome. Actual Safari/Firefox, device WebViews and production CSP/proxy deployments are outside this task. Plain iframe visitor persistence depends on browser partitioned storage; the widget saves the HMAC on its parent host.
- TASK-0226 retains the bilingual handbook and standalone example refresh; TASK-0228 retains platform wrappers/guides. This API contract and browser fixture do not mark those tasks complete.

## Standards And Architecture Alignment

One shared presentation, one SDK transport implementation; host widget stays plain JS/DOM per DEC-0079. Palette/labels derive from canonical shadcn tokens and en/vi dictionaries. Shared shadcn controls, errorText and existing exact-name destructive dialogs are reused. No new delete endpoint, catalogue code or database layer/schema change. Request-origin handling stays at the API boundary; router continues calling the existing authentication service.

UI checklist: colour/hex scans have no hits; no new hard-coded product colour, custom app control or node/template field. The plain host bubble is the approved widget architecture; token-based colours, accessible button labels/expanded/control attributes and iframe title are present. Strict class guard and locale checks are part of final validation. Screenshots are external temporary files.

## Design Alignment

Existing bubble/frame and published-page layout are retained. Theme/locale can update without discarding the current session. Public on/off, acknowledgement promises, ready/error and persisted-turn semantics are documented. Native-frame API uses the same methods with visibility events for its wrapper.

## Validation Review

Full eight-command Factory verification passed. The 16 existing chat regressions pass, and all three new widget/native scenarios pass on their final fixture. The expiry case observes actual CHAT_TOKEN_EXPIRED responses beyond the 60-second leeway before successful provider retries. Screenshots disable animations through Playwright, and dark-mode form/history controls are asserted to inherit the page's foreground. Initial fixture/animation wait problems and the concurrent-build interruption are documented in QA-0220; production source is unchanged after its full verification. Canonical root build/lint/tests are repeated for the final test/artifact delta.

## Assumptions

The host backend authenticates users before issuing bounded JWTs. Restricted iframe keys include the Studio origin, and reverse proxies correctly configure STUDIO_PUBLIC_URL. No release/merge approval is inferred.

## Required Follow-Up

Record final validation/QA and submit one Draft PR for owner review. Keep TASK-0225 out of done until owner acceptance.

## Review Decision

Approved for QA (advisory). Owner approval remains pending; submit a Draft PR.


## Owner Acceptance And Ready Finalisation (2026-11-03)

The owner accepted PR #290 ("Approve") after head e6b2f7c85b22eaae3d2428abb4f665ee5b0e4260 completed 21 successful CI checks and one expected GHCR publication skip. This includes all three Playwright shards, both backend databases, Factory full verification, React 18/19 host acceptance, SDK/CLI and image/security checks. This supersedes the earlier pending-owner-acceptance/Draft-only statements.

TASK-0225 moves to done on the same PR for a rebased, single-commit Ready delivery. Current develop remains 6218d840; production source, tests, API contract and dependency versions are preserved. Required validation is repeated on the rewritten head; its actual CI outcome is reported on #290 before delivery. Merge/tag/publication remains outside this acceptance.
