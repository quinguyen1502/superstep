# Review

## Metadata

- Project: superstep
- Review ID: REV-0259
- Task ID: TASK-0273
- Reviewer: Grok (advisory; not owner approval)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

`factory/req-0090-export-remaining` against `develop` `5f68852f`, PR #336, head `f52a2fc0`. This review covers the per-node LLM slots in `export_common.py`, `python_export.py`, `typescript_export.py`, the fallback tests, and `test_export_remaining.py::test_llm_slots_hide_ids_and_fall_back`. Approval and managed calls are reviewed on TASK-0274 and TASK-0275. Cross-language code nodes are unchanged.

## Reference Artifacts

- REQ-0090, DEC-0089, PLAN-0010, TASK-0273

## Findings

### Blocking

- None. No blocking findings.

### Non-Blocking

- The slot provider is read when the model is called. The generated `LLM_PROVIDER` name is read when the file is loaded. An unset slot still falls through to that name, which is what the existing fallback tests require.
- The TypeScript twin was not executed on this machine. CI backend pytest installs Deno, and factory verify passed on `f52a2fc0`.

## Standards And Architecture Alignment

- Credential ids are stored on internal keys and emitted only as `LLM_CRED_<n>`. The slot test refuses `primary-SECRET` and `backup-SECRET`.
- No new API error code. A missing live key raises in the generated process and names `<SLOT>_API_KEY`.
- The exporters stay in the engine. No router or service layer was added for slots.

## Design Alignment

- No product UI. Handbook rows in English and Vietnamese describe the slot. The strict handbook build passed on PR #336.

## Validation Review

- Local `tests/test_export_remaining.py` passed after `b6c9e52b`. PR #336 head `f52a2fc0` is green, including Backend pytest, Postgres/Redis, and verify (`https://github.com/quinguyen1502/superstep/actions/runs/42370418030/job/128397211110`).
- This review did not re-run the suite.

## Assumptions

- Optional fallback to `LLM_PROVIDER` when the slot provider is unset is the compatibility choice in DEC-0089.

## Required Follow-Up

- None before QA. Owner approval is still required before done, and merge is a separate request.

## Review Decision

approved for QA
