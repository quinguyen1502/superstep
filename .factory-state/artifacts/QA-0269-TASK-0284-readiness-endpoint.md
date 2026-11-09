# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0269
- Task ID: TASK-0284
- QA Owner: Grok (advisory)
- Created: 2026-11-09
- Updated: 2026-11-09
- Outcome: pass

## Acceptance Criteria Coverage

- Database down gives 503 from `/api/ready` while `/api/health` answers 200: pass (`test_database_down_gives_503_while_health_stays_200`); a slow database fails within the probe timeout (`test_database_probe_times_out_quickly`).
- Redis configured and down gives 503; Redis unset reports the in-memory bus and passes: pass (`test_configured_redis_down_fails_readiness_and_unset_redis_does_not`).
- Queue depth, delayed, processing and oldest queued age match Redis (fake Redis) and the database: pass (`test_redis_queue_depth_matches_the_lists`, `test_memory_queue_depth_counts_jobs_in_flight`, `test_oldest_queued_run_age`).
- Worker heartbeat age is reported and becomes stale when the worker stops: pass (`test_worker_heartbeat_is_reported_and_goes_stale`, `test_worker_counts_busy_slots_while_a_job_runs`).
- No secret, URL or host in either response: pass (`test_responses_carry_no_url_host_or_secret`).

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_readiness.py tests/test_schedules.py tests/test_health_version.py tests/test_layers.py tests/test_api_envelope.py`.
- Full backend suite (see the task log), `factory validate --only hygiene`.

## QA Decision

Pass.
