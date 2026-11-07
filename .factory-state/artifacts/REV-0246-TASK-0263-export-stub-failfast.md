# Review

## Metadata

- Project: superstep
- Review ID: REV-0246
- Task ID: TASK-0263
- Reviewer: Grok (advisory; owner authorised the fixes and green merge)
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

`backend/app/engine/python_export.py`, `backend/app/engine/typescript_export.py` (service stubs, missing-target branches only), `backend/tests/test_export_service_stubs.py`, `backend/tests/test_python_export.py` (stub constant), handbook `guide/python-export.md` en/vi, factory artifacts. Browser export code untouched.

## Findings

### Blocking

- None.

### Non-Blocking

- Offline mode still returns mock values by design (DEC-0087) so examples and Studio parity tests keep running; it is announced on stderr.
- `LLM_PROVIDER` doubles as the "real run" switch; a workflow without LLM nodes needs it set to opt into live behaviour. Documented.
- develop already has a REV-0242/QA-0242 number collision between TASK-0259 (merged first) and TASK-0251; not changed here (other agent's artifacts).

## Standards And Architecture Alignment

No secret or connection value added to generated code; only `LLM_PROVIDER` is read. Missing subgraphs fail only when reached, so unrelated branches still run.

## Review Decision

Approved for QA.
