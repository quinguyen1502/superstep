# Task

## Metadata

- Project: superstep
- Task ID: TASK-0116
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-25
- Updated: 2026-10-25
- Requirement IDs: REQ-0072
- Design IDs: none
- Architecture IDs: DEC-0063

## Objective

Implement the Agent node's engine: expand it into model and tool steps (DEC-0063), call models with tools through the
provider registry, run the four tool sources, and write the answer, steps and history, with the offline mock.

## Scope

### In Scope

- `engine/agents.py`: `expand(wf)` (entry, `__model`, `__tool`, `__exit`, routers, hidden `__agent__<id>` field),
  `step_budget(wf)`, `MAX_CALLS_PER_ROUND`; called after `subgraphs.expand` in `RunService`, in
  `WorkflowService` save-validation and in `runtime.py`'s recursion budget.
- Node functions for `agent`, `agent_model`, `agent_tool` and `agent_exit` (`engine/nodes.py` dispatch);
  `effects.SIDE_EFFECT_TYPES` gains `agent_model` and `agent_tool`.
- `Provider.invoke_tools` (base: `chat_model().bind_tools()`; Anthropic over its Messages API `tools`), streamed
  final text through `token_stream`, usage through the usage sink; `llm.mock_agent`.
- Tools: MCP (`ports.mcp_call`), knowledge base (`ports.retrieve`), built-in (`TOOLS`, `call_tool`), HTTP
  (`nodes.http_call` with the per-step idempotency headers); argument check (required properties, JSON types);
  error tool results; result shortening; `ports.cancelled` between steps; demo rule for HTTP.
- Round limit: the last call without tools, with `limit_hit` in the state and the trace event.
- Validator: model, prompt, output field, at least one tool, unique valid tool names, `max_rounds` 1 to 25, a known
  MCP server/tool and knowledge base reference, a provider with tool calling; `TYPES`/`WRITERS` updated.
- Error codes (for example `AGENT_TOOLS_UNSUPPORTED`) in `core/errors.py`, `docs/api-errors.md`, en and vi.
- `backend/tests/test_agent_node.py`.

### Out Of Scope

- Approval before a tool call (TASK-0117), the editor and trace UI (TASK-0118), tests check, template and exports
  (TASK-0119), handbook (TASK-0120).

## Inputs

- REQ-0072 (Owner Decisions), DEC-0063, CLAR-0003.
- `engine/subgraphs.py` (expansion pattern), `engine/foreach.py` (`step_budget`), `engine/nodes.py`,
  `engine/effects.py`, `engine/providers.py`, `engine/llm.py`, `engine/ports.py`, `engine/validator.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0072-agent-node.md`
- Design: none (UI in TASK-0118)
- Architecture: `.factory-state/decisions/DEC-0063-agent-node-expansion.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0018-effectively-once.md`,
  `DEC-0032-llm-provider-registry.md`, `DEC-0044-workflow-test-runs.md`
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0003-agent-node.md`

## Expected Outputs

- An `agent` node in a workflow JSON runs end to end through `/ws/run`, the API trigger and test runs, with the
  mock and with respx-mocked providers.

## Implementation Notes

- Keep the expanded nodes out of the saved workflow: expansion happens on a copy, as for subgraphs.
- Trace events for internal steps carry the agent id and the round so TASK-0118 can group them.
- `agent_exit` writes `steps` only when the steps field is set.

## Constraints

- Layers (DEC-0009): engine code only reaches services through `Ports`; no migration (settings live in the workflow
  JSON).
- No new Python dependency.
- Offline mock keeps working with no API keys.

## Dependencies

- None. Based on develop. Independent of TASK-0114 (#142) and TASK-0115 (#143).

## Acceptance Criteria

- pytest: an agent with the mock calls a tool and answers; respx-mocked OpenAI-compatible and Anthropic tool calls
  run MCP, HTTP, built-in and knowledge base tools and return their results to the model; the final answer and the
  steps field are written; the history field adds earlier turns.
- An unlisted tool, bad arguments and a failing tool give error results and are never executed; more than
  `MAX_CALLS_PER_ROUND` calls in one round are refused.
- At the round limit one call without tools gives the answer and `limit_hit` is set.
- Each tool call is its own step with its own ledger entry and idempotency key; a re-run of a finished step returns
  the ledger result (unit test on `Effects`).
- The validator reports each listed mistake; a TypeSafe credential gives the new error code.
- `tests/test_layers.py` and `tests/test_api_envelope.py` pass.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q` (new tests and the full suite); `factory verify run --profile full`.

## Assumptions

- LangChain `bind_tools` on the existing chat models covers OpenAI-compatible, LM Studio, OpenRouter and Ollama.

## Open Questions

- None.

## Activity Log

- 2026-10-25: planned from REQ-0072 (CLAR-0003 answered).
- 2026-10-25: started on `factory/task-0116-agent-engine-loop` from develop at bb70e04 plus the planning commits
  (REQ-0072, CLAR-0003, DEC-0063, TASK-0116..0120), which ride this task's PR; the owner accepted DEC-0063.
- 2026-10-25: implemented `engine/agents.py` (expansion, routers, step budget, the four step functions, tool sources,
  argument check), `llm.call_agent` / `llm.mock_agent`, `Provider.invoke_tools` (LangChain `bind_tools`; Anthropic
  Messages API over plain HTTP), tool parameter schemas in `engine/tools.py` (also in `GET /api/meta/tools`), validator,
  compiler routers, runtime expansion and budget, `RunService._expand`, `AGENT_TOOLS_UNSUPPORTED`;
  `tests/test_agent_node.py` (15 tests).
- 2026-10-25: review fixes (de0a7f5): HTTP tool arguments are never rendered as templates, schema type lists are
  accepted, run-until-agent runs the whole agent; service-path run and fork test (8acbd6d). Validation:
  `factory deps apply` passed; `factory verify run --profile full` passed every check except `python:backend:test`,
  whose only failures are the 6 environment tests that fail on develop in this container too (QA-0108). REV-0108
  approved for QA; QA-0108 pass with follow-up; DEC-0063 amended (field name, provider check at run time). Moved to
  review; Draft PR #144 into develop.
- 2026-10-25: PR #144 merged into develop (8503d20) with the owner's approval; moved to done by TASK-0120.

## Handoff Notes

- Review REV-0108, QA-0108. Next: owner review of the PR; `finish-pr` after approval and green CI.
- Trace events: `node_finished` of an agent step carries `agent` (what the step did: `kind` model|tool, `round`,
  text or tool call, result, status, `limit_hit`); the delta leaves the hidden `agent:<id>` field out, the `input` keeps
  it so time travel can fork inside the loop. TASK-0118 groups by `agent_of`.
- Scope notes: the validator checks that MCP server/tool and knowledge base references are set (as the MCP and
  Retriever nodes do), not that they exist; a provider without tool calling is caught when the step runs (the
  validator has no credentials). Cancellation needs no extra check: the run stops between steps, and every model
  call and tool call is a step. Exports still treat the node as a pass-through until TASK-0119.
