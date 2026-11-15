# Review

## Metadata

- Project: superstep
- Review ID: REV-0298
- Task ID: TASK-0313
- Reviewer: Codex
- Created: 2026-11-12
- Updated: 2026-11-12
- Outcome: Approved for QA

## Findings

- Preview is read-only. Import revalidates the same input, checks the schema revision and writes the definition and rows together for a new dataset. An existing dataset holds its revision lock until the append commits.
- Export projects active columns, checks read scope, includes all matching dataset rows independent of the grid page, and prefixes potential formulas in text and header cells.
- Import accepts up to 1 MiB and 1,000 records, shows the first 20 records and up to 100 issues, and uses column defaults for empty or unmapped values. Export returns an explicit error above 16 MiB. These are request bounds, not benchmarked throughput limits.

## References

- [Task](../tasks/done/TASK-0313-dataset-csv.md)
- [QA](QA-0298-TASK-0313-dataset-csv.md)
