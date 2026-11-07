# Task

## Metadata

- Project: superstep
- Task ID: TASK-0274
- Title: Export approval channel, deadline and AI review
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Requirement IDs: REQ-0090
- Design IDs:
- Architecture IDs: DEC-0089

## Objective

Export channel notices, deadlines, reminders and AI review for Human nodes and Agent tool approvals, without writing channel ids, targets or approver addresses.

## Scope

### In Scope

- Python and TypeScript helpers, fail-safe judge order, local daily cap, deadline wait.

### Out Of Scope

- Cross-language code nodes.
- Studio inbox delivery. The exported decision is the local answer.

## Inputs

- REQ-0090, DEC-0089, PLAN-0010, TASK-0273 slots for the judge.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0090-export-remaining-runtime.md`
- Design:
- Architecture:
- Decisions: `.factory-state/decisions/DEC-0089-export-remaining-runtime.md`
- Discovery:
- Clarifications:

## Expected Outputs

- Helpers emitted only when a node has a channel, a deadline or a parsed policy.
- Simple Human nodes keep `interrupt({ node:`.

## Implementation Notes

- Example answers return before a notice. "also asks on Slack" and "also go to a channel" stay in the file.

## Constraints

- Suggest never answers. Auto approves only on approve plus confidence. A missing cap file does not auto-approve.

## Dependencies

- TASK-0273 for the judge slot. Implemented on the same branch.

## Acceptance Criteria

- An auto reject rule returns rejected without asking a person.
- A short deadline applies `on_timeout`. A Slack webhook receives one POST when the run waits.
- Credential ids, channel ids and escalate addresses are absent.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest tests/test_export_remaining.py tests/test_python_export.py tests/test_typescript_export.py -q`

## Assumptions

- Operator webhook URLs are not pinned. Managed tool targets are pinned separately.

## Open Questions

- None.

## Activity Log

- 2026-11-07: Created and started with TASK-0273 and TASK-0275.
- 2026-11-07: Channel notice, deadline and AI review are in both exporters. Python tests cover a reject rule, a local Telegram post and a 0.2s approve-on-timeout. Deno was not run.
- 2026-11-07: `b6c9e52b` stops writing the judge instructions, which TASK-0188 forbids. PR #336 CI is green at that commit, including factory verify. Status stays doing until review and QA. Not merged.
- 2026-11-07: Review REV-0260 approved for QA. QA QA-0260 conditionally passed. Advisory only. Status stays doing. Not merged.
- 2026-11-07: Owner approved (duyệt). Moved to done with Review REV-0260 and QA QA-0260. Not merged.

## Handoff Notes

- Owner approved on 2026-11-07. The task is done. Do not merge until the owner asks.
