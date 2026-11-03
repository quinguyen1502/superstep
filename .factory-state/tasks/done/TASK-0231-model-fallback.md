# Task

## Metadata

- Project: superstep
- Task ID: TASK-0231
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-01
- Updated: 2026-11-01
- Requirement IDs: REQ-0083
- Design IDs: DES-0001
- Architecture IDs: DEC-0081

## Objective

Add opt-in primary/fallback model policy to LLM nodes without new graph node types, and record the generic integration delivery plan.

## Scope

### In Scope

- One fallback credential/model, validation, owner-bound resolution and bounded failover for provider failures.
- No partial output mixing, no failover on permission/cancellation errors, trace metadata for attempts and selected provider/model, usage of the successful attempt.
- Existing editor model controls plus fallback configuration, en/vi, handbook and CHANGELOG.
- Export behavior supports the policy or explicitly refuses an unsupported configured policy.

### Out Of Scope

- Managed tools, event bindings and expense template (subsequent PLAN-0003 tasks); Agent/Decision policy changes and arbitrary fallback lists.

## Inputs

- Owner's request to implement the three generic feature groups, 2026-11-01.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0083-event-connections-model-policy.md`
- Design: `.factory-state/artifacts/DES-0001-event-connections-model-policy.md`
- Architecture: `.factory-state/decisions/DEC-0081-event-connections-model-policy.md`
- Plan: `.factory-state/artifacts/PLAN-0003-event-connections-model-policy.md`
- Standards: `AGENTS.md`, `docs/backend-architecture.md`, `docs/ui-conventions.md`

## Expected Outputs

- Tested fallback policy, existing-workflow compatibility, UI evidence, review/QA and one Draft PR.

## Constraints

- `factory ready` must pass before implementation. No new dependency or migration expected. Follow existing envelope/catalogue/i18n/layers/theme conventions. No merge without owner approval.

## Dependencies

- None; starts from develop after TASK-0219 merged.

## Acceptance Criteria

- Disabled/absent policy has exactly existing behavior. Enabled policy validates both config fields, rejects inaccessible/non-chat credentials and cannot leak another owner's credential.
- Primary success does not call fallback; primary provider failure calls fallback once; both failures return a normal error; no fallback on cancellation/permission errors.
- Failed-primary partial tokens are not combined with fallback output; selected model and attempts are observable without secrets.
- UI configuration persists; mock remains offline; export never silently drops the policy.

## Validation Plan

- Focused backend policy/provider/validator/layer/envelope and export checks.
- Frontend build/lint/unit tests and browser regression with screenshots.
- Full `factory verify run --profile full`, `factory validate`, IDs and diff checks.

## Assumptions

- The owner's implementation request authorises the recorded scope and routine design defaults; PR merge remains a separate approval.

## Open Questions

- None blocking.

## Activity Log

- 2026-11-02: Owner explicitly approved merging PRs #278–#284 into develop and requested removal of all evidence screenshots. REV-0208/QA-0208 passed; this PR carries its own done transition and human approval, rebased onto current develop and squashed into one commit. Removed all image evidence from this tree, including older task-0217 screenshots; handbook illustrations remain. Screenshot evidence is intentionally no longer retained; textual validation records remain. Added ignore rules to prevent future evidence screenshots entering Git. Final-head CI gates the merge; no release or live cutover authorised.
- 2026-11-01: Implementation and advisory review/QA complete (REV-0208, QA-0208). Focused backend 57 passed, frontend 149 passed, full Factory eight checks passed, final build/lint and all five browser tests passed (48.8 s), bilingual handbook/media checks passed. Screenshots cover en/vi and light/dark. Entering review for Draft PR delivery; owner approval pending.
- 2026-11-01: `factory ready` passed with REQ-0083 and all four scoped tasks. Implementation starts on the dedicated branch from develop; owner already requested implementation, testing and delivery, so the narrow task-start checkpoint does not require a second confirmation.
- 2026-11-01: Planned under owner-authorised REQ-0083; first task is model policy because it is independent and needs no event/connection schema migration.

## Handoff Notes

- Branch `factory/task-0231-model-fallback` from origin/develop. Do not begin source work before readiness passes.
