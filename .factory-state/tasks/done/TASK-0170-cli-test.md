# Task

## Metadata

- Project: superstep
- Task ID: TASK-0170
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0071

## Objective

`superstep test` runs a workflow's test suite, writes JUnit XML, and exits non-zero when a case fails, so CI can gate a push.

## Scope

### In Scope

- DEC-0071 decision 6: `test <workflow>`, `test --all`, `--mock`, `--junit`.
- CLI catalog keys for the summary lines and `NO_TESTS`, en and vi.
- A fixture HTTP client that returns a running suite and then a finished suite. No new server route.

### Out Of Scope

- Editing, creating or deleting test cases.
- LangSmith upload.
- Changing how the suite itself runs.

## Inputs

- REQ-0079 group C (`test`) and REQ-0042.
- DEC-0071 decision 6.
- `backend/app/api/routes/workflow_tests.py`, `WorkflowTestService.public_suite`, the token loader from TASK-0167.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`, `.factory-state/artifacts/REQ-0042-workflow-tests.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0071-cli-workflows.md`
- Decisions: `DEC-0068-superstep-cli.md`
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`

## Expected Outputs

- `superstep-junit.xml` with one testsuite and one testcase per result.
- Exit 0 when every case passed, exit 1 otherwise.

## Implementation Notes

- Poll `GET /api/workflows/{id}/tests/runs/{sid}` until `status` is not `running`. Reuse the run timeout flag only if it is already on the shared parser; otherwise poll for 300 seconds and then exit 1 with the suite still running. Do not add a second timeout design. 300 seconds is the default, `--timeout` overrides it.
- `--all` lists workflows, skips those whose test list is empty, and still writes a JUnit file for the suites that ran. Zero suites is `NO_TESTS` and no file.
- Resolve an id or an exact name inside this command's module. If a shared helper is already on `develop`, call it. Register `test` from its own module.
- `--mock` sends `{"mock": true}`. Without it, send `{}`.

## Constraints

- No new dependency. Python >= 3.9. JUnit is written with the standard library (`xml.etree` or a hand-built escaped XML string). No new XML package.
- Catalog keys match across en and vi.
- The CLI does not import the backend.

## Dependencies

- TASK-0167 merged into `develop`.
- May proceed in parallel with TASK-0168, TASK-0169 and TASK-0171. Register the command from a new module so the parser file is not a shared edit conflict. If the workflow lookup helper is not on `develop` yet, vendor a private lookup in this module and switch to the shared one only if that other task has merged.

## Acceptance Criteria

- A suite with `failed: 0` and status `done` exits 0. A suite with one failed case exits 1. The JUnit file has a `failure` whose text includes that case's `reason`. A `cancelled` suite exits 1.
- `--junit out.xml` writes that path and does not write `./superstep-junit.xml`.
- `--mock` is the only request that sends `mock: true`.
- `--all` runs two workflows that have tests, skips one that has none, and exits 1 if either suite failed. When every workflow has no tests, the exit is `NO_TESTS`.
- `--help` includes an example. `--json` prints one object `{ok, suites}` and no XML on stdout. The XML is still written to the file.
- Summary lines are in the selected language.

## Validation Plan

- `cd sdk/python && python -m pytest -q` for the new tests, with a fake HTTP client and a temporary JUnit path.

## Assumptions

- The designer step is skipped. CI reads the exit code and the XML file.
- An empty `checks` failure still produces a `failure` element whose message is the status.
- `--all` does not stop at the first failed workflow. It finishes the list, then exits 1 if any failed.

## Open Questions

- None.

## Activity Log

- 2026-10-30: planned from REQ-0079 phase 2 (DEC-0071). Not started.
- 2026-10-30: implementation started.

- 2026-10-30: owner asked to finish the phase 2 chain in one pass. Review REV-0146. QA QA-0146. Task moved to done. Not merged.

## Handoff Notes

- Review REV-0146. QA QA-0146. Not merged.
