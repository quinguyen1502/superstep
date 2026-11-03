# QA Report

- Project: superstep
- QA ID: QA-0216
- Task ID: TASK-0221
- Created/Updated: 2026-11-02
- QA Owner: Codex, advisory
- Outcome: pass; owner accepted 2026-11-02
- References: REQ-0082, PLAN-0002, DEC-0077–0080, REV-0216, TASK-0221 in done

## Acceptance Coverage

- Shared token vectors: passed. Python standard-library signatures exactly match `sdk/fixtures/chat-token-vectors.json`, already verified by TASK-0220 with the real backend verifier. UTF-8/TTL/meta limits and non-leaking errors tested.
- Live streamed answer: passed in both sync/async transports through actual HTTP and websockets. `scripts/sdk_integration.sh`: Python 8 passed and TypeScript 7 passed, including Human text/form replies, upload/download/delete, rating, session/history and user isolation. Backend uses mock models, temporary SQLite/key files, no real credentials.
- Public chat surface: passed via the same recorded v1 frame contract for sync/async, anonymous bootstrap/persistence, static/callback tokens, no inherited workflow/studio credentials, expiry bounds, origin/revoke refusals, protocol additions/duplicates, dropped connection recovery and missing result safety.
- Lifecycle: passed cancellation, deadline, parent close, async task cancellation and close during baseline/authentication. No socket or write occurs after pre-dispatch close; result remains absent when execution was not confirmed. Context manager cleanup is documented; Python bare break alone is not advertised as deterministic cleanup.
- Packaging/version: base import and minting work with websockets blocked; chat extra reuses CLI's 15.0.1 pin, base dependencies remain httpx only, Python 3.9 syntax parses, and sdist/wheel build as the unchanged 0.10.2 shared package. Owner amended the obsolete 0.2.0 goal; no tag or publication.

## Validation Evidence

- Focused SDK regression (chat/client/async/spec-sync): 62 passed (1.01 s).
- Final complete Python SDK suite with local MCP HTTP fixture permitted: 217 passed, 8 skipped (13.61 s). Skips are live integration cases without environment configuration, separately passed by the isolated integration script.
- Full Factory profile on committed implementation 0c7c5b4: 8/8 passed. Backend 481.00 s, frontend build/lint/test 6.83/0.96/5.92 s, Python SDK 14.71 s, TypeScript build/test/typecheck 1.28/1.26/1.58 s. Final SDK-only close correction was followed by the complete Python suite; no backend/frontend source changed.
- Isolated package build creates `superstep-0.10.2.tar.gz` and `superstep-0.10.2-py3-none-any.whl`; no publishing command used.
- Final Factory validation, all-ref ID checks and whitespace gate precede push. Source CI status is recorded by the Draft PR checks.

## Limits And Handoff

No real provider/device/deployment tests or UI changes. HTTP and token-callback timeouts are separate from the socket deadline; synchronous callbacks cannot be forcefully interrupted. Network/cancel ambiguity requires a history reload, never an automatic resend. Native/browser cross-origin acceptance belongs to TASK-0222; screenshot evidence stays outside Git.

Task remains in review, stacked on unmerged TASK-0220/#285. Human approval is needed for merge/release. TASK-0222 is authorised separately and is implemented in an isolated stacked worktree.

## Owner Approval And Finalisation

Owner accepted the reviewed phase-2 stack on 2026-11-02 ("Duyệt"). TASK-0221 moves to done on existing #286, rebased onto finalised #285 and squashed for Ready delivery. No Python source changes are introduced by finalisation; the inherited reviewed fetch fix is now in #285. Shared version remains 0.10.2. Earlier pending/review entries are historical. Merge and publication are not authorised; exact-head CI must pass before delivery.

Finalisation rerun after restacking: complete Python SDK suite 217 passed, 8 live cases skipped (14.79 s); the isolated live cases are also required in exact-head CI. Factory validation, all-ref ID collision gate and whitespace check passed. No Python source difference from the owner-reviewed tree.
