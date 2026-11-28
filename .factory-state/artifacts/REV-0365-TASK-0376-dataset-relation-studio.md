# Review

## Metadata

- Project: superstep
- Review ID: REV-0365
- Task ID: TASK-0376
- Reviewer: Codex
- Created: 2026-11-28
- Updated: 2026-11-29
- Outcome: approved for integration pending final CI

## Scope

Reviewed Relation configuration, scoped target selection, read-only label projection, picker focus and revisions, identity filters and unlink confirmation. The Studio preview uses the existing Relation flag and authenticated backend endpoints.

## References

- [Task](../tasks/done/TASK-0376-dataset-relation-studio.md)
- [Design](DES-0008-dataset-formulas-and-relations.md)
- [Plan](PLAN-0020-dataset-formulas-and-relations.md)
- [QA](QA-0365-TASK-0376-dataset-relation-studio.md)

## Findings

### Blocking

- A 25-result picker initially placed pagination outside the viewport. Popover height now follows the available space and the result list scrolls independently of its footer. Playwright exercises both page controls. No blocking findings remain.

### Non-Blocking

- Label lookups batch visible row IDs by Relation field and abort when the source or visible range changes. A failed lookup shows an unavailable state. An authorized empty display value uses its row ID.
- Grid requests carry the schema and row revisions captured when the picker opens. A conflict preserves the saved link and offers reload. The shared unlink confirmation asks for the linked label when it is available.
- Schema authoring shows only visible Datasets in the source scope. An existing Relation target is immutable and its display column can be changed. The backend still authorizes every write.
- The bulk row editor shows Relation labels as read-only. Link editing is available in Rows. Connected and standalone writes and CSV link import remain separate milestones.

## Review Decision

The owner approved merging PR #437 on 2026-11-29 after review and QA. CI on the final head gates integration.
