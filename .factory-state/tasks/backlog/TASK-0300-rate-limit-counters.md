# Task

## Metadata

- Project: superstep
- Task ID: TASK-0300
- Title: Rate-limit hit counters
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

Show when Superstep's own limits reject requests, next to the provider-side limits already counted.

## Owner-Facing Outcome

Grafana shows how often sign-in, public chat, chat triggers, API triggers, approval callbacks, Code runs and the e-mail node quota are throttled, and a combined panel puts these next to provider 429s.

## Scope

### In Scope

- Product limits: `studio.rate_limit.hits` counter with label `scope` (fixed enum such as `login`, `demo`, `public_chat`, `chat_trigger`, `api_trigger`, `approval_callback`, `code`, `pat`, `email_node`), recorded once in the shared limiter path (`services/rate_limit.py` callers that raise `RATE_LIMITED`, and `services/email_quota.py` for `EMAIL_RATE_LIMITED`).
- Provider limits: already counted as `studio.llm.errors{code="PROVIDER_RATE_LIMITED"}` (TASK-0287); no duplicate counter, only a dashboard panel and a warning alert reuse it.
- `scope` added to `LABELS`; never the limiter key (it can contain a user id or IP). New metrics get panels in the provisioned Grafana dashboard under `deploy/observability/` in the same PR; the handbook observability page (en and vi) gets a short entry, and the full pass is TASK-0305.

### Out Of Scope

- Changing any limit value or response.

## Dependencies

- None (TASK-0287 merged).

## Acceptance Criteria

- Each throttled path increments the counter with its scope in a test; allowed requests do not.
- Limiter keys never appear in metric attributes (test).
- HTTP status, `Retry-After` and error bodies are unchanged.

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- None

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.

## Handoff Notes

- Use branch `factory/task-0300-rate-limit-counters` from `develop` when implementation begins.
