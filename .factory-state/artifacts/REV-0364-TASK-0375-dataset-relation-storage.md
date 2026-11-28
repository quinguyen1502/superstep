# Review

## Metadata

- Project: superstep
- Review ID: REV-0364
- Task ID: TASK-0375
- Reviewer: Codex
- Created: 2026-11-28
- Updated: 2026-11-28
- Outcome: approved for integration pending final CI

## Scope

Reviewed the additive migration, authenticated definition and row endpoints, lookup projection, Dataset writer locks, authorization after lock acquisition, deletion paths, capability boundaries and preview compatibility. The preview flag defaults off. Existing Studio reads can render a stored link identity where a preview Dataset exists. The Relation picker, Connected bindings and standalone exports are tracked in the following milestone.

## References

- [Delivery plan](PLAN-0020-dataset-formulas-and-relations.md)
- [Requirement](REQ-0102-dataset-formulas-and-relations.md)
- [Architecture](ARCH-0004-dataset-formulas-and-relations.md)
- [Task and acceptance criteria](../tasks/done/TASK-0375-dataset-relation-storage.md)

## Findings

### Blocking

- CSV create initially accepted the shared schema input with Relation metadata through a bulk-insert path. CSV preview and import now reject Relation definitions before creating data. Regression coverage verifies both paths. No blocking findings remain.

### Non-Blocking

- The edge key stores one target identity for each source cell. Database foreign keys supplement the application locks. Workspace cleanup rejects external references and removes internal outgoing edges before deleting their rows.
- A target Dataset and its source share a personal owner or team. The link transaction rechecks role, current membership, target scope, display column and row existence. The lookup rechecks target visibility in the row query and serves labels with `Cache-Control: no-store`.
- The Connected delete contract adds one conflict code with generic guidance. Public shares reject Relation fields. Source projections, CSV and audit events omit target labels. Generated projects reject Relation definitions until the related bindings are implemented.
- SQLite search sorts by a case-folded display value. The 25,000-row picker scan is the slowest measured preview operation. Record the benchmark for the later interactive picker review.

## Validation Review

- [QA evidence](QA-0364-TASK-0375-dataset-relation-storage.md) covers legacy upgrades, rollback protection, two-database link/delete races, revoked access, CSV and capability checks and preview rendering.

## Review Decision

The owner approved merging PR #436 on 2026-11-28 after review and QA. CI on the final head gates integration.
