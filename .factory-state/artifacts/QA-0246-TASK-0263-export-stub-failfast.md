# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0246
- Task ID: TASK-0263
- QA Owner: Grok (advisory)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: pass

## Acceptance Criteria Coverage

- Offline mock announced (Python, TypeScript/Deno) — pass (`test_*_offline_mock_is_announced`).
- Live run refused before any fake result (both) — pass (`test_*_live_run_refuses_unimplemented_services`).
- Missing subgraph fails naming the target (both) — pass (`test_*_missing_subgraph_fails_when_reached`).
- Existing Studio-parity export suites unchanged in behaviour — pass (python/typescript/project/handoff/browser export tests, 136 passed with Deno).

## Checks Performed

- pytest export suites with Deno 2 on PATH; full `factory verify run`; handbook strict build en/vi.

## Gaps Or Untested Areas

- Agent workflow-tool and unregistered-function raises are covered by generated-code inspection, not execution.
- Model fallback and HTTP parity are TASK-0264/0265.

## QA Decision

Pass.
