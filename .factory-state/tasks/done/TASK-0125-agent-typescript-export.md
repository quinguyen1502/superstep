# Task

## Metadata

- Project: superstep
- Task ID: TASK-0125
- Status: done
- 2026-10-26: PR #158 merged into develop (ec36bf5) with the owner's approval after CI passed (15 passed, 2 skipped); moved to done.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0072 (Agent node), REQ-0047 (TypeScript export)
- Design IDs: none
- Architecture IDs: DEC-0063 (Agent node as model and tool steps), DEC-0051 (TypeScript export)

## Objective

Export Agent nodes as LangGraph.js TypeScript. CLAR-0003 question 8 put this off ("TypeScript refuses the node with a
clear error until a later task"); the owner picked it as the next task in chat on 2026-10-26.

## Scope

- `engine/typescript_export.py` writes an Agent node the way `python_export.py` does (DEC-0063):
  - an entry node that starts the conversation in its own state field;
  - the model node and the tool node in a loop, with their routers;
  - an end node that writes the answer (and the steps, when the node has a steps field).
- The same helpers as the Python file: `callAgent` (offline mock unless `LLM_PROVIDER` is set, then LangChain.js
  `initChatModel` with `bindTools`), `checkArguments`, `toolText`, `shorten`.
- Every tool source:
  - built-in Python functions become stubs that throw, as the Tool node does;
  - knowledge and MCP tools call the existing `retrieve` / `callMcpTool` stubs;
  - HTTP tools call `fetch`.
- Tool approvals use `interrupt()`; `main()` answers them like Human nodes.
- `TYPESCRIPT_EXPORT_AGENT_UNSUPPORTED` is removed (errors catalog, `docs/api-errors.md`, both locales).
- Handbook (en, vi): the Agent guide and the export guide.

## Out Of Scope

- Porting built-in Python tool functions to TypeScript.
- Approval channels and deadlines (not part of LangGraph, as in the Python file).

## Acceptance Criteria

- A workflow with an Agent node (in the main graph or a subgraph) exports as TypeScript with no error.
- The file passes `deno check` and, run offline, takes the studio's mock path to the same final state as the studio:
  approve and reject of a tool that needs approval both match.
- No credential, server, knowledge base or channel id reaches the file.
- Built-in templates with an Agent node and no Python tool functions run in the TypeScript template tests.

## Validation

- `backend`: `pytest tests/test_typescript_export.py tests/test_python_export.py tests/test_api_envelope.py`, then the
  full backend suite.
- Deno tests run locally (Deno installed) and in CI.

## Changes

- `engine/typescript_export.py`:
  - an `AGENT` helper block (`callAgent`, `mockAgent`, `checkArguments`, `toolText`, `shorten` and their types);
  - `agent()` and `agent_calls()` write the four steps and the tool dispatch;
  - `buildGraph()` adds the steps, the loop edges, and the edges out of the end node (fan-in too);
  - the refusal is removed.
- `engine/export_common.py`: `http_key` and `rounds` moved up from the Python writer, so both exporters share them.
- The error code `TYPESCRIPT_EXPORT_AGENT_UNSUPPORTED` is removed from `core/errors.py`, `docs/api-errors.md` and
  both locales.
- e2e `agent-tests.spec.ts`: the Code tab now shows the `.ts` file.
- Handbook `guide/agent.md` and `guide/python-export.md` (en, vi), CHANGELOG (Unreleased).

## Validation Results

- Deno 2.9.8 locally (the official release binary; the Homebrew install failed on this machine).
- `tests/test_typescript_export.py` + `tests/test_code_typescript.py`: 57 passed, 2 skipped (Docker sandbox not
  running). New tests:
  - `test_agent_nodes_are_exported`: names, stubs, the HTTP query string, the approval question, and no `SECRET` value;
  - `test_agent_takes_the_studio_path`: approved, rejected with a reason, knowledge base, inside a subgraph;
  - `test_agent_builtin_tools_are_stubs_the_model_hears_about`;
  - `test_all_node_types_type_check` now covers the Agent workflow and the Support agent template.
- Full backend `pytest` (without Deno on PATH): 717 passed, 56 skipped.
- Not run: the LLM_PROVIDER path (it needs a real model). `deno check` type-checks it against LangChain.js.

## Review And QA

- Review: REV-0113, QA: QA-0113. Both were written after the merge, by TASK-0129 on 2026-10-26: the PR was merged on CI and the
  validation above, without them.
