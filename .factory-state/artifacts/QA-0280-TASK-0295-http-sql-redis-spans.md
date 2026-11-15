# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0280
- Task ID: TASK-0295
- QA Owner: Grok (advisory)
- Created: 2026-11-10
- Updated: 2026-11-10
- Outcome: pass

## Acceptance Criteria Coverage

- Flag off: no instrumentation package imported, run traces unchanged: pass (`test_off_imports_no_instrumentation`, `test_flag_needs_a_traces_exporter`, existing `test_telemetry.py`).
- Flag on: an API request yields an HTTP span (route template name) with SQL and Redis children; a run yields SQL and Redis spans under its trace: pass (`test_request_has_sql_and_redis_children`, `test_run_sql_and_redis_spans_join_the_run_trace`).
- No span attribute contains a SQL parameter value, a Redis value or an id from the key: pass (`no_values` in both tests, `test_redis_key_prefix_keeps_fixed_words_only`).
- Probe routes create no spans; LangSmith export filters out HTTP, SQL and Redis spans: pass (`test_request_has_sql_and_redis_children`, `test_langsmith_receives_only_run_and_node_spans`).
- An HTTP request that queues a run adds a span link to the run trace: pass (`test_queued_run_links_the_request`).

## Checks Performed

- `backend/.venv/bin/python -m pytest tests/test_spans.py tests/test_telemetry.py tests/test_observability_stack.py tests/test_layers.py`.
- Full backend suite and `factory verify run --profile full`, `factory validate` (see the PR).

## QA Decision

Pass.
