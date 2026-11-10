# Task

## Metadata

- Project: superstep
- Task ID: TASK-0297
- Title: Per-call LLM latency and time to first token
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-10
- Requirement IDs: REQ-0095
- Design IDs: 
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0014
- Phase: 2
- Size: S

## Objective

Measure each model call, not only whole runs, so slow providers or models stand out.

## Owner-Facing Outcome

Grafana shows p50/p95 latency and time to first token per model and provider, and an alert can fire when a provider gets slow.

## Scope

### In Scope

- `studio.llm.duration` histogram (ms) per call and `studio.llm.ttft` histogram (ms, streamed calls only) with labels `model`, `provider`, `status` (ok or error code class).
- Measured around `call_llm`, `call_agent` and the AI review path in `engine/llm.py` / `services/approval_service.py`; TTFT from the first non-empty streamed delta.
- Fallback calls are measured per attempt; mock calls are not recorded.
- Duration and TTFT also added to the model usage record so TASK-0301 can store them. New metrics get panels in the provisioned Grafana dashboard under `deploy/observability/` in the same PR; the handbook observability page (en and vi) gets a short entry, and the full pass is TASK-0305.

### Out Of Scope

- Per-call latency on the Usage page (operator metric, Grafana only).

## Dependencies

- None (TASK-0287 merged).

## Acceptance Criteria

- A mocked streamed call records one duration and one TTFT sample with the right labels; a non-streamed call records duration only.
- A failed primary plus a fallback records two durations with their own providers.
- Label set checked in tests; existing provider and run tests stay green.

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- None

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.

## Handoff Notes

- Use branch `factory/task-0297-llm-latency-ttft` from `develop` when implementation begins.
