# Review

## Metadata

- Project: superstep
- Review ID: REV-0355
- Task ID: TASK-0366
- Reviewer: Codex
- Created: 2026-11-21
- Updated: 2026-11-21
- Outcome: Approved for QA

## Review Scope

Reviewed the Formula schema form, non-mutating preview endpoint, diagnostic display, and read-only guard across the grid, CSV and workflow editors.

## Reference Artifacts

- [Task](../tasks/done/TASK-0366-dataset-formula-studio.md)
- [Design](DES-0008-dataset-formulas-and-relations.md)
- [Formula persistence](../tasks/done/TASK-0365-dataset-formula-persistence.md)

## Findings

### Blocking

- No blocking findings.

### Non-Blocking

- The preview selector uses the first 20 stored rows as examples. Empty datasets expose sample input controls. General enablement and standalone project exports remain separate work.

## Standards And Architecture Alignment

- Preview uses the shared Dataset API, manager permission checks and current schema revision. It clones the candidate into the loaded schema without committing or allocating generated values.
- Studio reuses shadcn controls, theme tokens, existing row selection and scalar formatting, and both locale catalogs. Formula outputs are selectable and omitted from write mappings.
- Formula validity feedback is evaluated after blur or on preview/save. Cell diagnostics stay in the normal row height, provide an accessible name, and keep formula results read-only.
- The opt-in gate applies to configuration. Existing computed rows remain readable when the preview setting is off.

## Review Decision

Approved for QA in the stacked branch.
