# Review

## Metadata

- Project: superstep
- Review ID: REV-0227
- Task ID: TASK-0254
- Reviewer: Codex (advisory self-review)
- Created/Updated: 2026-11-05
- Outcome: no blocking findings; owner UI accepted and locally validated candidate

## Scope And Acceptance

Review covers the full diff against develop: shared chat actions/focus rings, separate workflow history/ratings, four owner screenshot batches, plain collapsible heading, panel tabs, managed export placeholders and v0.11.1 preparation. Owner explicitly approved all previews and requested remaining work and patch preparation. Prior requirement/decision approvals are preserved. Task, branch, PR #300, REV and QA IDs are reused. No merge/publication instruction is inferred.

## Findings

No blocking source findings. Root MCP, Agent tools and child graph exports use explicit raising/throwing TODO helpers without copying connection settings/secrets. Export annotations are temporary and cleared before resource lookup. Code/ZIP and placeholder-execution tests pass; export performs no external send. Backend layers, envelopes, catalogue and schema remain intact; no migration/dependency is introduced.

The clean-install React pin mismatch found in early CI is fixed to 0.1.1 with matching lock metadata. Installed backend wheel smoke found missing socket JSON schemas; package-data now includes them and installed health/AsyncAPI work. Shared app/Python/CLI/frontend version is 0.11.1; React is 0.1.1 and TypeScript SDK remains 0.2.0.

## Standards / UX / Access

Existing shadcn components/theme tokens and matching en/vi strings; shared attached Tabs variant and plain chevron header. Message items reserve focus-ring paint space while preserving alignment/virtualisation. Existing APIs retain published-page/current-user visibility; workflow history does not expose other Studio users' private sessions. Read-only turns/Save-as-test remain. Exact-name deletion and plain DELETE semantics are preserved; no screenshots or build artefacts are committed.

## Evidence And Remaining Gates

Factory full profile passes 8/8, final build/lint and installed-package checks pass, en/vi handbook builds pass. Initial browser failures were old UI interactions, corrected and verified in focused reruns (see QA-0227). All final combined browser/CI checks must pass on the final PR head before handoff/merge. The original 16941171 CI is historical only.

The separately reported real public-page first-message rejection needs its URL/environment. A tested session rejection/retry remains inline, while metadata still enforces publication. Release notes do not claim the unknown remote root cause fixed. Physical-phone/keyboard and native TASK-0227/0228 remain outside this patch. Finish-pr carries done/Ready on the same single-commit candidate; merge/tag/upload/deploy remain unperformed.
