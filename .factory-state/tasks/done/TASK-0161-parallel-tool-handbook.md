# Task

## Metadata

- Project: superstep
- Task ID: TASK-0161
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-30
- Requirement IDs: REQ-0076
- Design IDs: none
- Architecture IDs: DEC-0069

## Objective

The handbook, the changelog and the operator docs describe parallel tool calls, and the Support team template shows two desks running in one round.

## Scope

### In Scope

- Handbook, en and vi:
  - `handbook/docs/en/guide/agent.md` and `handbook/docs/vi/guide/agent.md`: replace the lines that say a round's calls run one after another. State the default (on), the per-node switch, the cap of 4, the order of results, and that a failure or an approval does not stop the other calls.
  - `handbook/docs/en/guide/python-export.md` and `handbook/docs/vi/guide/python-export.md`: the sample that says `support_agent_tool` runs one call, updated to the graph TASK-0160 emits.
- `docs/deploy/env-vars.md` and `docs/deploy/env-vars.vi.md`: `STUDIO_AGENT_PARALLEL_TOOLS`, default 4, range 1..8.
- `CHANGELOG.md`: an unreleased entry for parallel Agent tool calls.
- e2e, en and vi: the Support team template, one message that names `order_desk` and `refund_desk`, both child runs started in that round, the trace bars overlapping. Follow `frontend/e2e/workflow-tools.spec.ts`.

### Out Of Scope

- Comparison pages. They do not describe the sequential loop.
- Changing the Support team template's existing test cases. Those messages call one desk on purpose.
- Engine, waits, the switch and the exports, except for the words that quote them (TASK-0157 to TASK-0160).

## Inputs

- DEC-0069 decisions 1, 2, 8 and 9.
- The shipped behaviour of TASK-0157 to TASK-0160.
- `handbook/docs/en/guide/agent.md` (the sentence at the round running one after another), and the same section in `handbook/docs/vi/guide/agent.md`.
- `frontend/e2e/workflow-tools.spec.ts`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0076-parallel-agent-tool-calls.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0069-parallel-agent-tool-calls.md`
- Decisions: `.factory-state/decisions/DEC-0063-agent-node-expansion.md`, `.factory-state/decisions/DEC-0066-workflow-tools-child-runs.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0007-parallel-agent-tool-calls.md`

## Expected Outputs

- A reader of the Agent page, in either language, sees that a round's calls run together unless the node turns that off.
- An e2e run of the Support team template, in en and in vi, shows both desks starting in one round.

## Implementation Notes

- The offline mock returns both tools only when the message names them (DEC-0069 decision 9). The e2e message must contain `order_desk` and `refund_desk`. A natural-language question that only shares description words still calls one desk, and the existing template cases stay that way.
- Overlap in the e2e is the two tool rows of that round being visible together, with bars that start together. Use the trace test ids already in `run-trace.tsx`.
- Do not add a third Support team test case to `engine/templates.py` unless the e2e cannot drive the template without it. The requirement's e2e is the check.
- Changelog tone matches the current unreleased section. Do not invent a version number.

## Constraints

- Handbook en and vi say the same facts. Env-var tables en and vi gain the same key.
- UI strings the e2e reads stay in the locale files. This task does not add a screen.
- No new dependency.

## Dependencies

- TASK-0157, TASK-0158, TASK-0159 and TASK-0160 merged to `develop`.

## Acceptance Criteria

- The Agent handbook page, en and vi, no longer says that the calls of a round run one after another. It states the default, the switch, the cap and the result order.
- Both python-export pages describe the concurrent path TASK-0160 generates, and the sequential path when the setting is off.
- Both env-var pages document `STUDIO_AGENT_PARALLEL_TOOLS` as default 4, clamped to 1..8.
- CHANGELOG has an unreleased bullet for this behaviour.
- e2e, en and vi: using the Support team template and a message that names both desks shows both calls in one round, and the two bars share their start. The run reaches an answer.
- `cd frontend && npm run e2e` for the Support team spec passes in both languages.

## Validation Plan

- `cd frontend && npm run e2e` for the Support team spec, en and vi.
- Read the four handbook pages and both env-var pages against DEC-0069.

## Assumptions

- The e2e app runs with the offline mock, as the current Support team spec does.
- "Two desks in one round" is shown by naming both tool names. A real provider does this from the question text without those names. The mock cannot, without breaking the one-desk template cases.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0076 (DEC-0069). Medium-task workflow.
- 2026-10-30: delivered with TASK-0158 to TASK-0160 on PR #213 (`69d55a2`). Review of that PR left no blockers after `b16c468`. QA: the handbook build and the Support team e2e passed, and CI on `b16c468` was green. Owner merged. Moved to done. REQ-0076's tasks are all done.

## Handoff Notes

- The handbook (en, vi), `STUDIO_AGENT_PARALLEL_TOOLS`, and the CHANGELOG describe the default of 4 and the per-node switch.
