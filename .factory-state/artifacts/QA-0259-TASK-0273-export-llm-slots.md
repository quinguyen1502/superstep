# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0259
- Task ID: TASK-0273
- QA Owner: Grok (advisory; not owner approval)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: pass with follow-up

## Validation Scope

Per-node LLM slots on PR #336 head `f52a2fc0`. Evidence is the green CI run and the Python slot test. This QA did not start a new suite. Review is REV-0259.

## Acceptance Criteria Coverage

- Criterion: Two credentials become `LLM_CRED_1` and `LLM_CRED_2`. The ids are absent.
  - Result: pass
  - Evidence: `tests/test_export_remaining.py::test_llm_slots_hide_ids_and_fall_back`. `primary-SECRET` and `backup-SECRET` are refused. Calls pass `slot="LLM_CRED_1"` and `fallback_slot="LLM_CRED_2"`.
- Criterion: A set slot provider and key are selected. A missing key names `<SLOT>_API_KEY`.
  - Result: pass
  - Evidence: The same test sets `LLM_CRED_1_PROVIDER` to `anthropic`, expects `RuntimeError` matching `LLM_CRED_1_API_KEY`, then with the key and base URL expects provider `anthropic` and those kwargs.
- Criterion: An unset slot still uses `LLM_PROVIDER`, including the existing fallback tests.
  - Result: pass
  - Evidence: The same test expects provider `openai` from `LLM_PROVIDER` when the slot provider is unset. CI Backend pytest on Python 3.12 passed, which includes `tests/test_export_model_fallback.py` and `tests/test_export_fallback_files.py`. Run `https://github.com/quinguyen1502/superstep/actions/runs/42370417978/job/128397211356`.

## UX And Accessibility Coverage

- Criterion: No product UI. Handbook rows exist in both locales.
  - Result: pass
  - Evidence: `handbook/docs/en/guide/python-export.md` and `handbook/docs/vi/guide/python-export.md`. Strict build passed: `https://github.com/quinguyen1502/superstep/actions/runs/42370417971/job/128397210938`.

## Checks Performed

- Inspected `llm_slot`, `resolve_model` / `resolveModel`, and the slot test.
- Referenced PR #336 CI on `f52a2fc0`. Factory verify passed: `https://github.com/quinguyen1502/superstep/actions/runs/42370418030/job/128397211110`.
- GHCR publish and handbook deploy were skipped, as on other pull requests into `develop`.

## Defects

- None.

## Gaps Or Untested Areas

- TypeScript `resolveModel` was not executed locally. Deno is absent on this machine. CI installs Deno and the backend job passed.

## Residual Risk

- A file loaded before `LLM_PROVIDER` is set keeps the empty module value. Slot variables are read at call time.

## Assumptions

- Falling back to `LLM_PROVIDER` when the slot provider is unset is intentional.

## Required Follow-Up

- None for this criterion set. The task stays in doing until the owner accepts review and QA.

## QA Decision

conditionally passed with documented risk
