# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0271
- Task ID: TASK-0285
- QA Owner: Grok (advisory)
- Created: 2026-11-09
- Updated: 2026-11-09
- Outcome: pass

## Acceptance Criteria Coverage

- With an in-memory reader all gauges and counters appear with allowed labels only: pass (`test_gauges_report_probes_queue_worker_and_process`, `test_in_memory_flag_is_zero_with_redis`, `assert_bounded`).
- With metrics off the OTel metrics SDK is not imported: pass (`test_metrics_off_does_not_import_the_metrics_sdk`).
- Reaped and recovered jobs increment their counters: pass (`test_reaped_and_recovered_jobs_are_counted`).
- `studio.run_bus.in_memory` is 1 only with the in-memory bus: pass.
- Run metrics keep their meaning and gain `workflow_id`: pass (`test_run_metrics_carry_the_workflow_id`, `test_node_spans_are_exported_live_and_metrics_recorded`).

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_metrics.py tests/test_model_fallback.py tests/test_telemetry.py tests/test_deferred.py tests/test_readiness.py tests/test_layers.py tests/test_api_envelope.py`.
- Full backend suite and frontend locale tests (see the PR), `factory validate --only hygiene`.

## QA Decision

Pass.
