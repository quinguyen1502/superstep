# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0293
- Task ID: TASK-0308
- QA Owner: Codex
- Created: 2026-11-12
- Updated: 2026-11-12
- Outcome: Pass
- Review ID: REV-0293

## Validation Scope

Rating and suite aggregates, Usage quality card, LangSmith settings link, bounded submission counter and Grafana chart and alert. Product diff reviewed at `83dfb83f` on PR #363.

## Acceptance Criteria Coverage

- Criterion: Seeded ratings match expected rates and small samples are identified.
  - Result: Pass
  - Evidence: Seeded API results and the Vietnamese preview confirmed a reported rate at five or more ratings, a small-sample row and the latest completed suite.
- Criterion: Saving a rating increments the counter with exactly the allowed labels.
  - Result: Pass
  - Evidence: An in-memory metric reader observed a single count with rating and workflow_id after a saved rating. Invalid input did not increment it. Synthetic submissions matched the Grafana alert query.
- Criterion: The admin endpoint returns 403 for other users and locale keys stay in parity.
  - Result: Pass
  - Evidence: The backend usage API coverage checks users.manage and the frontend locale test passed. The Grafana preview confirmed that the count chart displays values above one.

## UX And Accessibility Coverage

- The Usage card reports saved ratings and completed suite totals. Grafana uses submission counts with only approved metric labels. LangSmith results remain in LangSmith.

## Checks Performed

- [Full Factory verification](https://github.com/quinguyen1502/superstep/actions/runs/43122223869)
- [Product CI and three Playwright shards](https://github.com/quinguyen1502/superstep/actions/runs/43122223833)
- Local checks and preview evidence are listed above.

## Defects

- No open blocking defects.

## Gaps Or Untested Areas

- The Usage table reports the current saved rating per answer. The Grafana counter counts submissions, so changing a rating produces another submission.

## QA Decision

Passed to done. The final delivery commit will run through the required GitHub checks before merge.
