# Task

## Metadata

- Project: superstep
- Task ID: TASK-0209
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Requirement IDs: REQ-0065 (reliable test suite), REQ-0048 (chat)
- Design IDs: none
- Architecture IDs: DEC-0052, DEC-0067, DEC-0009, DEC-0010

## Objective

Fix at the cause, without retries, longer timeouts or skips, the three Playwright specs that failed in CI after #263:
`agent-chat.spec.ts:57` (shard 1/3 on the PR's first run), `notifications-deliveries.spec.ts:41` and
`profile.spec.ts:42` (shard 2/3 on develop, run 41181868855). Check whether the profile page really sends a write for
a read-only account.

## Findings

Evidence from the CI traces (`gh run download`), then a deterministic reproduction: a throwaway Playwright hook (not
committed) slows only the step the trace showed slow, and the unchanged specs fail every time with the CI error.

- `notifications-deliveries.spec.ts:41`, **test bug**. The trace has one click on Refresh and three reads of the
  delivery log, all `[]`, then nothing for 20 s. The poll body called `row...textContent()`, which waits for the row:
  when the first read came before the delivery was logged, the predicate never returned, so Refresh was never clicked
  again. Repro (first three log reads empty): 5 of 5 failed with `Timeout 20000ms exceeded while waiting on the
  predicate`. The poll now reads without waiting (`allTextContents()`), so every round refreshes.
- `profile.spec.ts:42`, **test bug, no read-only write**. The two PUTs in the trace carry `{"lang":"vi"}` at
  07:50:04.402 UTC, 28 ms after the test installed its read-only `/api/me` override and listener and before
  `/settings/profile` loaded: the sign-in language sync of the account just registered, which is a normal editor
  account at that point. Nothing on the profile page or in the notification settings writes for a read-only account
  (the dialog's switches are disabled and the language save checks `read_only`), and the API refuses such a write with
  403 `DEMO_READ_ONLY` (`test_demo_mode.py` covers `PUT /api/notifications/preferences`). Repro (slow first `/api/me`,
  slow next document): 4 of 5 failed with the two `lang` PUTs. The override is now in place before sign-up, so the
  account is read-only from its first page and every non-GET to the preferences is counted. The sync also went out
  twice (StrictMode mounts the switcher twice); one save per language is in flight now.
- `agent-chat.spec.ts:57`, **product bug plus a test race**. The session read after the approval has the turns
  `refund A1`, the waiting question, and the final answer: the person's answer `approved` was never saved (only shown as
  the pending bubble), so it vanished when the session was read again and the question stayed the last turn, still
  `waiting`. Between the run socket closing and that read, the composer was enabled and saw the old waiting question,
  so a message sent then went out as a second answer to the finished run (refused, and the read that followed cleared
  its pending bubble). In the CI run the socket was still open, so Enter did nothing (`refund A2` is still in the box
  in the screenshot) and the list then showed `refund A1` last. Not an equal-timestamp ordering: the turns have
  distinct `created` values. Repro (socket close 1.5 s late, session read 1 s late): 5 of 5 failed with
  `Expected "refund A2", Received "refund A1"`. Fixes: the answer is saved as the person's turn when the resume is
  planned (studio socket and public chat page), so it stays and the run is answered once; the chat stays `running`
  until the saved reply is read, and a read for an older message no longer clears a newer one; the spec waits for the
  composer to take a message (no Stop button) before typing, as a person would.

Earlier flaky fixes (TASK-0109, TASK-0196) fixed wrong assumptions in the tests; none of the three specs was touched
before, and no timeout was raised here.

## Acceptance Criteria

- Each failure explained from its CI trace and reproduced deterministically before the fix.
- The same reproductions and plain repeat runs pass after the fix; no retries, skips or longer timeouts.
- A Human answer from the chat is saved once as the person's turn (studio and public page).
- `factory verify run --profile full` and `factory validate` pass; CI green, all three E2E shards included.

## Validation

- Before (develop 2ec712b4): plain `--repeat-each 15` 45/45 and 45/45 with 3 workers and 8 CPU burners (the races
  need the CI timing); with the reproduction hook chat 0/5, deliveries 0/5, profile 1/5.
- After: with the reproduction hook chat 10/10, deliveries 10/10, profile 10/10; plain `--repeat-each 15` 45/45,
  and 45/45 with 3 workers and 8 CPU burners.
- Backend: `test_chat_sessions.py::test_visitor_answers_the_human_node_in_the_chat` and
  `test_public_chat_runs.py::test_a_visitor_answers_a_human_node_but_not_a_reviewers` assert the saved answer turn
  and that a second answer is refused.

## Review And QA

- Review: `.factory-state/artifacts/REV-0197-task-0209.md`. QA: `.factory-state/artifacts/QA-0197-task-0209.md`.

## Activity Log

- 2026-10-31: created from the owner's request to review and fix the flaky E2E specs after #263; implemented on
  `factory/task-0209-e2e-race-fixes` from `develop` (2ec712b4). Moved to done on this PR before the merge (TASK-0148).
