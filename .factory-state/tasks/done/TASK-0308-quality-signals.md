# Task

## Metadata

- Project: superstep
- Task ID: TASK-0308
- Title: Quality signals: thumbs-down and eval results
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-10
- Updated: 2026-11-12
- Requirement IDs: REQ-0095
- Design IDs: DES-0006
- Architecture IDs: DEC-0094, DEC-0095
- Plan: PLAN-0014
- Phase: 3
- Size: M
- Review: `.factory-state/artifacts/REV-0293-TASK-0308-quality-signals.md`
- QA: `.factory-state/artifacts/QA-0293-TASK-0308-quality-signals.md`

## Objective

Show answer quality next to usage, from the ratings and test data Superstep already stores.

## Owner-Facing Outcome

Settings, Usage shows thumbs-down rate per workflow (from chat answer ratings) and the latest workflow test suite pass rate, and Grafana can alert when the thumbs-down rate jumps.

## Scope

### In Scope

- SQL from `chat_ratings` (index on `workflow_id`, `updated`; add an index on `updated` if the windowed studio-wide query needs it) and `workflow_test_suites` totals; top workflows by thumbs-down rate with a minimum sample size.
- Counter `studio.chat.ratings` (labels `rating`, `workflow_id`) when a rating is saved; alert on a thumbs-down share spike.
- LangSmith evaluation results stay in LangSmith; the page links to the existing LangSmith settings when configured instead of copying results.
- en and vi strings; handbook section.

### Out Of Scope

- New rating UI or eval runner.
- Automatic model or prompt changes.

## Dependencies

- None technically; scheduled after phase 2 (TASK-0305) per PLAN-0014.

## Acceptance Criteria

- Seeded ratings produce the expected thumbs-down rates; workflows below the minimum sample show "not enough ratings".
- Saving a rating increments the counter with only allowed labels.
- API 403 without `users.manage`; en/vi parity passes.

## Validation Plan

- Targeted backend tests (`pytest`) and, where the frontend is touched, `npm run lint`, `npm run build`, `npm test` and the matching Playwright spec.
- Full `factory verify run --profile full` and `factory validate`; REV and QA artifacts; all required CI including the three E2E shards green before merge.

## Open Questions

- None

## Activity Log

- 2026-11-10: Created by planning on branch factory/plan-observability-next. No implementation. Stays in backlog until the owner accepts REQ-0095 and PLAN-0014.
- 2026-11-12: Moved from backlog to todo after the Phase 2 stack merged. Owner approved starting Phase 3 on 2026-11-11.

- 2026-11-12: Owner approved implementation. Added the quality card, scoped rating aggregation, latest test suite rows, rating submission telemetry and the alert. Ratings use the existing workflow and update timestamp index.

- 2026-11-12: Seeded data matched the expected thumbs-down share, minimum sample and latest completed suite. This branch is stacked on factory/task-0307-slo-burn.

- 2026-11-12: The thumbs-down alert expression matched synthetic submissions above its threshold.

- 2026-11-12: Grafana preview with synthetic ratings verified that the submissions panel scales above one rating.

- 2026-11-12: Owner approved merge. Moved to done on PR #363.

## Handoff Notes

- Use branch `factory/task-0308-quality-signals` from `develop` when implementation begins.
