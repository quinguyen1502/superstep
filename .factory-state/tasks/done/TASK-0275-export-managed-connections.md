# Task

## Metadata

- Project: superstep
- Task ID: TASK-0275
- Title: Export managed connection calls
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0090
- Design IDs:
- Architecture IDs: DEC-0089

## Objective

Replace the managed-connection placeholder with real adapter calls whose settings and secrets come from the environment. A call without a prefix, including an invalid browser connection, still raises the placeholder.

## Scope

### In Scope

- telegram, slack, whatsapp, teams, http_api, email, google_sheets, google_drive and web.
- Pinned HTTP, no redirects, local outcome journal.

### Out Of Scope

- Browser connections that already have a policy (they keep `browser_call`).
- Cross-language code nodes.

## Inputs

- REQ-0090, DEC-0089, PLAN-0010
- `backend/app/services/managed_tools/`

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0090-export-remaining-runtime.md`
- Design:
- Architecture:
- Decisions: `.factory-state/decisions/DEC-0089-export-remaining-runtime.md`
- Discovery:
- Clarifications:

## Expected Outputs

- `managed_operation(tool, arguments, prefix, adapter)` for a real adapter.
- `managed_operation(tool, arguments)` still raises the placeholder.

## Implementation Notes

- Lands on `factory/req-0090-export-remaining` with TASK-0273 and TASK-0274.
- Google token URL stays `https://oauth2.googleapis.com/token`.

## Constraints

- Do not write server ids, chat ids or secrets into the file.
- Unknown outcomes are not retried. Unconfigured offline is a dry run, not a confirmed send.

## Dependencies

- None.

## Acceptance Criteria

- A telegram export posts once to a local API when the environment is set, returns the stored result on the same arguments, and does not retry HTTP 500.
- The server id and secret values are absent.
- An invalid browser export still contains `Managed connection placeholder` and does not contain `browser_call(`.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest tests/test_export_remaining.py tests/test_managed_tools.py tests/test_browser_python_export.py::test_invalid_browser_settings_stay_a_placeholder -q`

## Assumptions

- `managed_placeholders` stays true whenever a managed reference exists, including a real adapter. The flag means the graph uses a managed connection, not that the helper is a stub.

## Open Questions

- None.

## Activity Log

- 2026-11-07: Created and started with TASK-0273 and TASK-0274.
- 2026-11-07: A named adapter exports `managed_operation` from `MANAGED_<n>` JSON. Python tests cover Telegram idempotency, conflict and an unknown outcome that is not retried. A missing adapter stays the placeholder. Deno was not run.
- 2026-11-07: PR #336 CI is green at `b6c9e52b`, including factory verify. Status stays doing until review and QA. Not merged.
- 2026-11-07: Review REV-0261 approved for QA. QA QA-0261 conditionally passed. Advisory only. Status stays doing. Not merged.
- 2026-11-07: Owner approved (duyệt). Moved to done with Review REV-0261 and QA QA-0261. Not merged.

## Handoff Notes

- Owner approved on 2026-11-07. The task is done. Do not merge until the owner asks.
