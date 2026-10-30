# Task

## Metadata

- Project: superstep
- Task ID: TASK-0180
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0078
- Design IDs: none
- Architecture IDs: DEC-0073

## Objective

Route a run from one Agent node to another when the model calls a hand-off tool, with checkpoints, the limit, and trace steps.

## Scope

### In Scope

- Each target becomes a tool `transfer_to_<slug>` with an optional `reason` (DEC-0073 decision 2).
- `expand` adds a router after `A/__exit`: a private state field `__handoff` set by the hand-off call routes to the target's entry; otherwise the agent's own outgoing edges.
- A hand-off is its own step `A/__handoff` with a checkpoint, so a pause, crash or restart neither repeats nor loses it.
- The target's conversation: the person's messages and agents' replies, without tool calls and results, plus the reason.
- Limit: a run counter; past `max_handoffs` the hand-off tools are removed and the model is told to answer itself.
- Same round with a hand-off and other tool calls (REQ-0076 waves): the hand-off wins; other calls get "not run: the conversation was handed off".
- Trace step "Triage › handed off to Billing" with the reason.
- Tests: routing, limit, mixed round, restart right after the hand-off step, time travel across a hand-off, subgraph scope.

### Out Of Scope

- Chat session memory (TASK-0181).
- Exports (TASK-0183).

## Inputs

- REQ-0078 'Engine', 'Limit', 'Trace', edge cases; DEC-0073 decisions 2 and 3.
- `engine/agents.py` (expansion, waves), `engine/compiler.py`, `services/time_travel.py`, `services/run_worker.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0078-agent-handoff.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0073-agent-handoff.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0009-agent-handoff.md`

## Expected Outputs

- Mock-model runs hand off and finish with the target's answer.

## Implementation Notes

- Prefer a conditional edge on a private field over LangGraph `Command(goto)` so the existing expansion, checkpoints and exports stay uniform (DEC-0073 decision 2).

## Constraints

- Layers of DEC-0009: routes call services, services call repositories, no FastAPI in a service, no SQLAlchemy in a route. `tests/test_layers.py` passes.
- Every API error uses the common envelope with an English error code listed in `core/errors.py` CATALOG, `docs/api-errors.md`, and `frontend/src/locales/en.json` and `vi.json`. `tests/test_api_envelope.py` passes.
- UI uses shadcn/ui components and theme tokens only. en and vi locale files keep the same keys.
- Schema changes go through a new Alembic revision after the latest one on `develop` at branch time.
- No new heavy dependency.

## Dependencies

- TASK-0179.

## Acceptance Criteria

- Triage → Billing with a mock hand-off: the final state has Billing's answer; the trace has the hand-off step with target and reason.
- The (N+1)th hand-off is refused and the run still ends with an answer.
- A restart right after the hand-off step continues at the target with no step repeated.
- Mixed round: the other tool calls are answered as not run.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd backend && .venv/bin/python -m pytest -q tests/test_layers.py tests/test_api_envelope.py`

## Assumptions

- The designer step is skipped. REQ-0078 and its CLAR already describe the screens.

## Open Questions

- None. DEC-0073 is accepted.

## Activity Log

- 2026-10-30: planned from REQ-0078 (DEC-0073). Status todo. Not started.
- 2026-10-30: owner confirmed the task set and accepted the decision record.
- 2026-10-30: implemented on `factory/task-0180-agent-handoff-engine` from `develop`. The engine runs agent hand-offs: transfer tools, the hand-off step, the target with the carried conversation, the run limit `factory verify run --profile full` passed. The owner authorized the merge of the REQ-0077/REQ-0078 task PRs. Moved to done on this PR before the merge (TASK-0148).

## Handoff Notes

- Branch `factory/task-0180-agent-handoff-engine` from `develop`.
- Review: `.factory-state/artifacts/REV-0157-task-0180.md`. QA: `.factory-state/artifacts/QA-0157-task-0180.md`.
