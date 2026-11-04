# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0227
- Task ID: TASK-0254
- QA Owner: Codex
- Created/Updated: 2026-11-05
- Outcome: local pass with documented follow-up; final-head CI required before handoff/merge

## Acceptance

Owner accepted all four screenshot batches and later plain-heading/focus fixes, then authorised remaining checks and preparing v0.11.1. This final report supersedes original-head QA; it does not inherit earlier CI. See TASK-0254 and REV-0227 for approved scope and source review.

## Verification

- Factory full profile: 8/8 declared checks pass, including full backend, root build/lint/test and Python/TypeScript SDK commands. Root unit coverage includes 157 frontend, 21 React and 102 TypeScript SDK cases. Python SDK: 229 pass/eight optional skips. Backend includes layers/envelope and managed root/Agent/child export coverage.
- Final root build/lint, Factory structure/policy/ID checks and diff whitespace check pass. Readiness warning about no new todo task concerns an already-started task; initial ready gate passed before implementation. Installation-receipt warning follows deliberate version/lock changes, with clean-install smoke and CI covering the manifests.
- Local full browser sweep: 179 collected cases. Original shard results were 45/49/47 pass, 13/4/6 skip, 8/5/2 fail. The failures targeted previous Config defaults, split schema, expanded disconnected channels or embedded visitor history. Do not call those original runs green. Corrected reruns pass: migration 7; attachments 2; fallback 4; code/Decision/template 5; code/editor/loop 2; Human deadline 1. Final combined suite is required in remote CI.
- Shared feedback geometry and keyboard ordering pass en/vi light/dark at 320/390/1280px, including persisted/read-only comments and complete focus-ring paint space. Public-session rejection stays inline and recovers on a real local retry.
- Python/backend wheel+sdist 0.11.1 build; installed backend health and AsyncAPI/socket schemas work; installed CLI reports 0.11.1. React 0.1.1 tarball imports and includes scoped CSS. Clean-manifest npm ci dry run passes. TypeScript SDK stays 0.2.0. No migration is added.
- Final en/vi handbook builds pass. Owner-approved source preview gallery has 48 theme-paired PNGs plus focused-input image, with final plain-heading views refreshed. All screenshots/traces/logs/distributions stay outside Git.

## Evidence

Under /private/tmp/superstep-0254-: final-factory-verify.log; final-build.log; final-lint.log; full-e2e-{1,2,3}.log; e2e-migration-followup.log; e2e-attachments-followup.log; e2e-model-followup.log; e2e-final-config.log; e2e-code-foreach.log; e2e-deadline.log; installed-{health,cli,react}.log; lock-smoke.log; handbook-{en,vi}.log. Generated Factory summary: .factory-state/verification/latest.yaml (ignored state). Distribution files: /private/tmp/superstep-0.11.1-dist. External gallery: existing superstep-review-0254 directory under Codex visualizations.

## Gaps / Delivery Boundary

Unknown public deployment URL is still needed to diagnose its original session rejection; only the bounded inline-error/retry behaviour is claimed. Local Chrome does not replace physical phone/soft-keyboard coverage. Optional Postgres/Redis/S3/Docker and final combined UI coverage rely on configured CI. Native TASK-0227/0228 remains deferred.

Task moves to done within finish-pr on the same owner-approved single-commit candidate. Final PR head must have green required CI before handoff/merge; fresh receipt is the check list on PR #300. No merge, tag, registry publication or deployment occurs under preparation-only authorisation.
