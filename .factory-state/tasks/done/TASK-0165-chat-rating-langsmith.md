# Task

## Metadata

- Project: superstep
- Task ID: TASK-0165
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0075
- Design IDs: none
- Architecture IDs: DEC-0070

## Objective

When LangSmith tracing is configured, send a saved chat rating to the run's trace as feedback, without making the
visitor wait.

## Scope

### In Scope

- Saving a rating enqueues `{kind: "chat_rating", turn_id}`.
- `RunWorker` handles that kind by calling `LangSmithService.on_rating`.
- `on_rating` sends `user_rating` (1 or 0) and the comment when the API key is set, tracing is on, and the run has
  `trace_root`. The first call creates the feedback and stores `feedback_id`. A later rating updates it.
- A LangSmith error is logged. The rating row stays. Deleting a rating does not enqueue a job.
- pytest with a fake LangSmith client: one create, a second rating updates, a raising client leaves the rating.

### Out Of Scope

- The evals studio setting. Chat feedback follows tracing (`LANGSMITH_TRACING`), not the test-suite evals switch.
- Handbook prose (TASK-0166). One sentence there can mention it.

## Inputs

- TASK-0162's table, including `feedback_id`.
- `services/langsmith.py`, `services/run_worker.py`, `api/deps.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0075-chat-answer-feedback.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0070-chat-answer-feedback.md`
- Decisions: `DEC-0052-web-chat-model.md`, REQ-0050's LangSmith client (`services/langsmith.py`)
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0006-chat-answer-feedback.md`

## Expected Outputs

- A configured LangSmith project shows `user_rating` on the run. A down LangSmith does not fail the rating.

## Implementation Notes

- `client_factory` is the test seam already used for suite feedback.
- `on_rating` catches errors the way `on_suite_done` does, so the worker does not retry a down endpoint into a second
  create.

## Constraints

- The HTTP handler returns before the LangSmith call.

## Dependencies

- TASK-0162.

## Acceptance Criteria

- With a fake client, one rating creates one feedback with key `user_rating` and score 1 or 0, and the comment.
- Rating again updates that feedback and does not create a second one.
- When `create_feedback` raises, the rating is still stored and the handler does not raise.
- With no API key, `on_rating` does not call the client.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q tests/test_chat_ratings.py`

## Assumptions

- Feedback is attached to the root span LangSmith already uses for the run link (`run_id_of(trace_root)`).

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0075 and DEC-0070.
- 2026-10-27: implemented and moved to review. Renumbered before push: DEC-0069 and TASK-0157 to TASK-0161 are held on factory/task-0157-parallel-tool-waves (REQ-0076). Draft PR #204.
- 2026-10-27: REV-0134, no blocking findings, approved for QA. QA-0134 pass with follow-up. Task stays in review.
- 2026-10-27: owner approved ("duyệt"). REV-0134 has no blocking findings. QA-0134 passed with the documented follow-ups. Moved to done. Not merged.

## Handoff Notes

- Removing a rating leaves the LangSmith feedback in place (DEC-0070 risks).
