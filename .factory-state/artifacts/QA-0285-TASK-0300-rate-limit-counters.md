# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0285
- Task ID: TASK-0300
- QA Owner: Grok (advisory)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: pass

## Acceptance Criteria Coverage

- Each throttled path counts with its scope; allowed requests do not: pass (`test_each_limiter_scope_counts_only_refusals`, `test_email_quota_counts_the_refusal`).
- Limiter keys never in metric attributes: pass (`test_limiter_keys_never_reach_metric_attributes`).
- Status, `Retry-After` and error bodies unchanged: pass (`test_login_lock_counts_with_the_same_response`, existing rate limit tests in the full suite).

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_activity_metrics.py tests/test_hardening.py tests/test_email_node.py`.
- Full backend suite and `factory verify run --profile full`, `factory validate` (see the PR).

## QA Decision

Pass.
