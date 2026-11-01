# Task

## Metadata

- Project: superstep
- Task ID: TASK-0234
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-01
- Updated: 2026-11-02
- Requirement IDs: REQ-0083
- Design IDs: DES-0001
- Architecture IDs: DEC-0081

## Objective

Prove generic events/tools/model policy with the owner's expense flow, and document complete Superstep setup without n8n.

## Scope

### In Scope

- Portable expense workflow/template using existing LLM/Code/Condition/MCP nodes, separate expense/submission dates, amount validation and explicit reply-after-confirmed-write.
- Mocked end-to-end Telegram/event -> model -> Sheets -> reply coverage, duplicate delivery and ambiguous write checks, model fallback and failure paths.
- Bilingual setup/operation guide, example configuration with placeholders, screenshots and CHANGELOG.

### Out Of Scope

- Real credential provisioning, production webhook cutover, live expenses, n8n import, expense approval process or app/package releases.

## Inputs

- Owner's n8n expense JSON (use sanitised example data only), REQ-0083 and the implemented PLAN-0003 features.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0083-event-connections-model-policy.md`
- Design: `.factory-state/artifacts/DES-0001-event-connections-model-policy.md`
- Architecture: `.factory-state/decisions/DEC-0081-event-connections-model-policy.md`
- Plan: `.factory-state/artifacts/PLAN-0003-event-connections-model-policy.md`
- Review: `.factory-state/artifacts/REV-0211-task-0234-expense-integration.md`
- QA: `.factory-state/artifacts/QA-0211-task-0234-expense-integration.md`
- Standards: `AGENTS.md`, `docs/ui-conventions.md`

## Expected Outputs

- Working generic integration example, browser/E2E evidence, docs and review/QA in its Draft PR.

## Constraints

- No actual bot ids, sheet ids, user ids or credentials in fixtures/templates. Model output cannot authorise tool targets or choose secrets. Google sheet stores plain untrusted text safely.

## Dependencies

- TASK-0231, TASK-0232, TASK-0233. Explicitly record stacked delivery if not merged.

## Acceptance Criteria

- Valid expense writes one record then confirms; missing/invalid amount or unrelated text does not write.
- Both model failure and malformed JSON are visible; fallback works; Sheets errors/unknown outcomes never produce a false success reply.
- Duplicate event/worker replay does not blindly produce duplicate expenses. Setup guide explains admission, credential scope, date rules and safe production cutover.
- Both handbook language builds and complete declared checks pass.

## Validation Plan

- Focused backend integration tests and browser workflow checks with screenshots, all outbound providers mocked.
- Handbook en/vi builds and media checks; full Factory verification, validation, IDs and diff check.

## Assumptions

- The initial status remains "Chờ duyệt"; actual approval is future scope. Full REQ-0083 closes only after all feature PRs are approved and merged.

## Open Questions

- No blocking local questions; actual production connection and cutover remain owner decisions.

## Activity Log

- 2026-11-02: Final landing rebased onto develop 2f01e14 after #278/#279/#280/#282/#283/#284 each merged with 20 passing checks. Shared test configuration was verified on the combined source before this rebase; only roadmap status conflicts remained and were resolved preserving all completed tasks. This final task closes REQ-0083; no tracked evidence screenshots remain. One commit on the same PR #281, with final full integration CI required before merge.
- 2026-11-02: Pre-integrated this example with the full managed-adapter stack at prepared Drive parent 72e00c5. Resolved changelog/test-config conflicts while preserving Expense/Drive/SMTP options and refusing simultaneous Expense+Drive fixtures. Combined source a4e78c3: 133 backend passed (46.21 s), expense browser four (34.9 s), Drive browser four (39.3 s), default MCP/session four (23.7 s), fixture guard and both handbook builds/media passed. Text evidence only; screenshots removed/ignored. Final rebase onto merged develop and full integration CI remain required before merging this same PR.
- 2026-11-02: Owner explicitly approved merging PRs #278–#284 into develop and requested removal of every evidence screenshot. Existing review/QA passed; this PR carries TASK-0234 to done with human approval and is squashed to one task commit. All evidence images are removed from the branch; historical screenshot paths in review/QA are intentionally retired while textual checks and handbook images remain. Rebase onto latest develop and final-head integration CI gate merge. No release or live provider cutover authorised.

- 2026-11-02: Final committed source 7b030b2 passed all eight full Factory checks (backend 474.02 s) and #281 CI (7m46s). Both handbook builds/media and final validation/ID/diff checks passed. REV-0211/QA-0211 passed locally; owner review pending. Follow-up commit records verification only; no implementation change. Other feature PR checks green, including #280 after its isolated rate-limit test fix.
- 2026-11-02: Rebased onto final TASK-0233 parent 4aa3a60 (including the isolated rate-limit test fix); own source snapshot 7b030b2. Draft #281 targets factory/task-0233-managed-tools (#280). Both handbook builds/media, artifact uniqueness and diff check passed; full profile running on that committed source. Fresh all-ref ID scan returns REV/QA-0212 because this branch now owns 0211; no collision against origin/develop.
- 2026-11-02: Portable 12-node template and bilingual setup/cutover guide implemented; resource refs blank. Combined focused suite 67 passed, including 19 expense cases; final browser four passed in 35.9 s with eight screenshots. Real parser executed with synthetic providers. Advisory review passed; full verification remains pending before final delivery. Move to review for the same task Draft PR; no merge approval inferred.
- 2026-11-02: `factory ready` exited 0 with TASK-0234 eligible in todo before this final task moved to doing; no source work started before that gate. Readiness checks for at least one todo task, so the normal final lifecycle move was performed after the successful pre-implementation check.
- 2026-11-02: Explicit stack on TASK-0233 at d1f9eb4 (factory/task-0233-managed-tools), above #279/#278 per PLAN-0003. Clean branch at start; parent full verification repeats in its isolated checkout after a test-only fixture cleanup. Deliver a portable Superstep template file through existing import/use, with all resource references blank. Seven data columns preserve the original expense fields and add submission timestamp; the managed adapter adds the eighth operation-id column. The graph uses explicit parsing, routing and confirmed-write gating. Production cutover remains an operator action after review.
- 2026-11-01: Planned under owner-authorised REQ-0083.

## Handoff Notes

- Branch `factory/task-0234-expense-integration-example`, Draft https://github.com/quinguyen1502/superstep/pull/281; base factory/task-0233-managed-tools at 4aa3a60. Land after #278 → #279 → #280, then retarget/rebase onto develop and wait for integration checks. No merge approval inferred.
