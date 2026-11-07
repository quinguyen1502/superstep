# Plan

## Metadata

- Project: superstep
- Plan ID: PLAN-0010
- Status: active
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Related Requirements: REQ-0090
- Related Design:
- Related Architecture: DEC-0089

## Objective

Land per-node model slots, approval export and managed-connection calls in one branch, without cross-language code nodes.

## Context Reviewed

- REQ-0090 and DEC-0089
- TASK-0266 proposal
- `backend/app/engine/python_export.py`, `typescript_export.py`, `export_common.py`
- `backend/app/engine/approval_policy.py`, `deadlines.py`, `approval_judge.py`
- `backend/app/services/mcp_service.py` `check_export`
- `backend/app/services/managed_tools/`

## Work Breakdown

- Task: TASK-0273
  - Purpose: Per-node `LLM_CRED_<n>` slots on both exports.
  - Dependencies: None.
  - Validation: `backend/.venv/bin/python -m pytest tests/test_export_model_fallback.py tests/test_export_fallback_files.py tests/test_export_remaining.py`
  - Required Artifacts: REQ-0090, DEC-0089
- Task: TASK-0274
  - Purpose: Channel notice, deadline, reminders and AI review in both exports.
  - Dependencies: TASK-0273 for the judge slot.
  - Validation: `tests/test_export_remaining.py` and the existing export tests that mention Slack.
  - Required Artifacts: REQ-0090, DEC-0089
- Task: TASK-0275
  - Purpose: Real managed-connection calls from environment JSON. Invalid browser stays a placeholder.
  - Dependencies: None.
  - Validation: `tests/test_export_remaining.py`, `tests/test_managed_tools.py`, `tests/test_browser_python_export.py::test_invalid_browser_settings_stay_a_placeholder`
  - Required Artifacts: REQ-0090, DEC-0089

## Sequence

1. Record the requirement, decision and these tasks. Note the owner's decline on TASK-0266.
2. Implement all three on `factory/req-0090-export-remaining` because the exporters are shared.
3. Update the handbook in English and Vietnamese.
4. Run the export tests. Review and QA come after the owner asks. Do not merge until the owner asks.

## Risks

- Shared exporter edits can break fallback signatures. The tests are updated to the new `slot` parameter and still assert the same failover calls when the slot environment is unset.

## Approval Needs

- The owner already accepted the requirement and declined cross-language code. Merge still needs a later request.

## Assumptions

- TASK-0274's judge uses the slot from TASK-0273. The tasks still ship in one commit series on one branch.

## Open Questions

- None.

## Completion Criteria

- The three task files exist and the exports match DEC-0089.
- REQ-0086 and REQ-0089 stay not done.
- Cross-language code nodes are unchanged.
