# Review

- Project: superstep
- Review ID: REV-0216
- Task ID: TASK-0221
- Created/Updated: 2026-11-02
- Reviewer: Codex self-review; advisory, owner accepted 2026-11-02
- Outcome: approved for QA
- References: REQ-0082, PLAN-0002, DEC-0077–0080, TASK-0221, QA-0216

## Scope And Findings

Own diff above TASK-0220/#285 at 1a45311: Python sync/async chat HTTP/socket APIs, lazy iterators/final results, stdlib token signing, optional chat extra, tests/README and live CI integration. No backend schema/UI/source change. No unresolved blocking findings.

Shared envelope/error parsing, frame state, history matching, request/file builders and claim validation have one implementation for sync/async callers; only I/O differs, following the existing SDK pattern. Config now allows chat-only base URLs and checks workflow credentials when a workflow starts. Chat never implicitly uses the parent's workflow token. Raw HTTP requests suppress borrowed cookies, default auth/headers/query parameters and redirects. Optional socket imports are lazy and no new base dependency is added.

JWT vectors match TASK-0220 and the backend, including literal UTF-8 secrets and Unicode claims. TTL/user/name/meta sizes, malformed/non-finite metadata and secret-safe errors are bounded. Auth uses headers/frames rather than URL query strings. Callable tokens refresh once on explicit expiry only, socket retry is pre-execution only, and origin/revocation refusals cannot refresh. Read-only recovery requires a new persisted assistant turn for a known run ID; missing acknowledgements never confirm or resend.

Iterators use websocket queue/frame/text limits and deterministic context-managed cleanup. Timeouts, task cancellation, client close and the final pre-dispatch close race are tested. File expiry retries restore seekable file positions; non-rewindable bodies cannot be replayed. HTTP results remain additive dictionaries; final streaming results are typed dataclasses. No form builder, UI package, publication or merge is included.

## Owner Amendment And Validation

The owner chose keeping the Python SDK/CLI/server version together; the task's obsolete standalone 0.2.0 target is superseded. The source remains 0.10.2 until an owner-approved shared release. websockets 15.0.1 reuses the existing CLI pin and Python >=3.9 support.

Recorded/shared-vector focused regression 62 passed; final complete Python SDK suite 217 passed, 8 live cases skipped without configured backend. Live Python workflow/chat 8 and TypeScript workflow/chat 7 passed on isolated mock services. Full Factory profile passed all eight checks on 0c7c5b4; final SDK-only lifecycle correction was rechecked by the complete Python suite. sdist/wheel builds and Python-3.9 syntax check passed. CI matrix and the Draft PR record remote results; physical/mobile UI is outside this task. Owner review is separate from this advisory review.

## Owner Approval And Finalisation

Owner accepted the reviewed phase-2 stack on 2026-11-02 ("Approve"). TASK-0221 moves to done on existing #286, rebased onto finalised #285 and squashed for Ready delivery. No Python source changes are introduced by finalisation; the inherited reviewed fetch fix is now in #285. Shared version remains 0.10.2. Earlier pending/review entries are historical. Merge and publication are not authorised; exact-head CI must pass before delivery.
