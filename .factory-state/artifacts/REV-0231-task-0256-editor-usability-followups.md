# Review

## Metadata

- Project: superstep
- Review ID: REV-0231
- Task ID: TASK-0256
- Reviewer: Codex (advisory, not owner approval)
- Created/Updated: 2026-11-05
- Outcome: approved for QA (same-task re-review after owner-authorised fixes)

## Latest Re-Review And Decision

Owner subsequently approved merge and release 0.11.2. Prior reviewed head 763432b2 passed all 22 executing remote checks, including Postgres 17/Redis 7, three Playwright shards and image security/smoke; GHCR publication is correctly skipped for PRs. Move TASK-0256 to done on the same PR, with one-commit finish and exact-head validation still gating merge. Physical-device coverage remains a documented manual follow-up.

Reviewed final implementation 7c7fc06a (documentation checkpoint 8abb6ac4) against unchanged origin/develop 3c83262a. No blocking findings remain from the three findings below:

1. Non-checkpointing **chat-only** runs now upsert bounded running snapshots and publish only after persistence at run start/resume and node boundaries. The `live_history` marker is display-only; queued/fenced recovery is unchanged, and memory startup recovery cancels orphan display rows instead of replaying side effects. A gated public socket test proves persisted running/progress before completion; real-browser public chat shows running→completed with zero Studio navigations.
2. Observer receive/push/heartbeat now share one AnyIO task-group lifetime. Redis pub/sub closes under a cancellation shield. Normal close, repeated reconnect, subscriber release and permission revocation pass on memory and local Redis/RESP2. A separate publisher process reaches the socket. No test exceptions were suppressed.
3. The shadow regression checks visible paint geometry rather than exact CSS serialization. It waits for Radix focus restoration and dialog animations, then exercises named creation, duplicate validation, immediate selection, Undo, keyboard outline and mobile fixed header/footer. All selected UI cases pass. Follow-up screenshot inspection also found and fixed negative duration for active rows with no ended timestamp.

**Validation:** canonical Factory full profile on the final source passes **8/8**: root build 11.87s, lint 1.24s, tests 17.27s; backend 447.23s; Python SDK tests 15.16s; TypeScript SDK build/test/typecheck 1.54/1.29/1.47s. A task-local arm64 Node launcher addresses the host's Python-spawn architecture mismatch without changing dependencies. `verify validate`, `factory validate` and diff checks pass; known install-receipt/no-todo warnings remain. Independent full backend: 1194 passed / 66 skipped in 463.23s. Focused backend: 56 passed / 1 skipped. Selected UI: 22 passed in 1.8m; runtime UI: 3 passed, 2 opt-in handbook captures skipped.

The UI conventions checklist was reviewed: shared shadcn controls/theme tokens, en/vi parity, existing delete confirmation paths unchanged, templates retain TemplateEditor, keyboard focus preserved, both-theme preview evidence retained outside Git. Backend layers/envelope tests pass; no package, migration, permissions expansion or release/version change. General uses real metadata/edges, creation stays explicit and undoable, and saved-chat settings disclose the workflow save.

**Non-blocking residual gaps:** Redis 7 and physical-device keyboard/native drag-ghost pixels remain unverified. Redis 5.0.5/RESP2 evidence is not production-version acceptance. Running socket snapshots are not a new durable replay/heartbeat guarantee, particularly on hard process loss in a Redis deployment. Full-history refresh after invalidation retains existing read permissions and can be optimised separately if needed.

**Decision:** approved for QA and Draft PR preparation; not owner merge/release approval. Final QA is QA-0231. Logs: /private/tmp/superstep-0256-fix-factory-final.log, /private/tmp/superstep-0256-fix-backend-final.log, /private/tmp/superstep-0256-fix-e2e-extra-final.log. Final public running/completed captures: /private/tmp/superstep-0256-final-ui-results. Earlier failed rounds are retained below for audit and are superseded by this re-review.

## Historical Review (Before Owner-Authorised Fixes)

## Review Scope

Reviewed checkpoint ce9c81281c4cb9fa894ca370d0ec5d7c3dadacbd against origin/develop 3c83262a: shared Alert/Button, palette drag image, panel Tabs, DialogBody conversions, empty Select menus, General connections, state-field actions and saved-chat settings, Studio chat history updates, workflow-history WebSocket/NotificationHub and new regression tests.

## Reference Artifacts

- .factory-state/tasks/done/TASK-0256-editor-usability-followups.md
- docs/ui-conventions.md
- docs/backend-architecture.md
- vision.md, project.md, roadmap.md

## Findings

### Blocking

1. **Cross-tab public runs are not published from their actual start or each node's progress.** RunPlan defaults checkpointing=false (backend/app/services/run_service.py:45); PublicChatService plans socket chat without enabling it (backend/app/services/public_chat_service.py:242). The new history notification runs only after record() or _save_progress(), and execute() calls _save_progress only for checkpointing plans (run_service.py:901,917). ChatSessionService.write() records the chat turn/message, not a running Run row. Thus the preview and current E2E prove arrival at waiting/terminal persistence, not immediate visibility of a long-running public run. This misses the owner's “start chat → run is immediately in the log” criterion outside Studio. Persist a bounded running/progress snapshot without changing execution/recovery semantics, notify after commit, and add a slow/public-run regression that checks before completion.
2. **Subscription-close regression is not green.** Three new backend tests fail reproducibly with concurrent.futures.CancelledError when the history WebSocket context exits, both on memory and Redis/RESP2 (runs_ws.py:46–54). Auth denial and share revocation tests pass; that does not resolve normal cleanup/reconnect failures. Investigate cancellation-safe task/subscription teardown and rerun the exact tests; do not suppress the test exceptions as a substitute for fixing/understanding cleanup.
3. **Two UI regressions stop before exercising the new state/Undo/dialog checks.** editor-followups.spec.ts:19 compares computed boxShadow to the exact string 'none'. Tailwind returns five fully transparent zero-sized shadow layers. This is an over-specific assertion, not evidence of a visible shadow. Check the actual absence of a visible shadow, retain focus-outline coverage and run the rest of each case. The present result cannot claim automated state creation/Undo/mobile-dialog acceptance.

### Non-Blocking

- Ordinary lint succeeds with existing/related React warnings. No hard-coded colour/dependency/migration was introduced; preview uses mock data and external image evidence.
- Redis available locally is 5.0.5, whereas the project deploys Redis 7. An initial Redis run failed HELLO/RESP3; a URL-only protocol=2 diagnostic got past that environment mismatch and reproduced the same three cleanup failures as memory. It is not production-version Redis evidence.
- Native OS drag-ghost pixels and a physical phone keyboard remain unverified. Source implements clipped drag-image snapshots and existing owner preview covers other UI states; do not imply native rendering QA is complete.
- History invalidations read the existing full authorised workflow history. Pagination/delta reads can be a later scalability improvement, not a new abstraction in this task.

## Standards And Architecture Alignment

Routers call RunService for visibility; services contain no FastAPI or raw SQL and reuse repositories/hub. UI uses shadcn/theme tokens and en/vi keys. Workflow-history push is content-free and per-run checked; history remains under existing permissions. New fields are explicit/undoable drafts; saved-chat settings disclose the workflow save. Exact-name delete conventions are unchanged.

## Design Alignment

Owner approved 27 screenshot previews and explained runtime behaviour with “OK, approved”, authorising validation and PR preparation, not merge/release. Geometry previews match the requested direction. Findings above prevent full acceptance despite preview approval.

## Validation Review

Independent root npm build, lint and all 280 npm unit tests pass. Targeted Playwright: 19 passed / 2 failed (shadow assertion). Focused backend live history: 2 passed / 3 failed in memory and Redis/RESP2. Full backend: 1188 passed / 65 skipped / 3 failed (the same new cancellation tests), 469.46s pytest / 472.67s runner.

The full Factory profile finishes failed (3/8 pass): root build/lint/test and SDK TS test fail native bindings under x64 Node spawned by the x64 Python runner; backend fails the three real cleanup tests. Direct shell Node is arm64; an explicit Python subprocess probe reports x64. Independent exact root npm commands run on arm64 pass; SDK Python, TS build and TS typecheck pass in Factory. This environment diagnostic is not a source fix, a standalone blocker task, or a claim that canonical verification is green. Logs: /private/tmp/superstep-0256-factory-full.log, build/lint/units logs; latest.yaml now records this task's failed run, not the older green one.

## Assumptions

No source fixes are performed by task-validation/task-review. Keep the task doing and preserve failures. No PR exists yet; do not use finish-pr or claim Ready/done.

## Required Follow-Up

Resolve findings 1–3 in the same task/branch, add pre-completion public-run coverage, rerun declared/full and focused checks, then update this review and QA. Check Redis 7/multi-process delivery when available and document native-device residual risk honestly.

## Historical Review Decision

Rejected to development. No merge, release or Ready recommendation.
