# Task

## Metadata

- Project: superstep
- Task ID: TASK-0372
- Title: Add sharing controls and a public Dataset viewer
- Status: backlog
- Owner: Thái Quí Nguyễn
- Created: 2026-11-22
- Updated: 2026-11-22
- Requirement IDs: REQ-0103
- Design IDs: DES-0009
- Architecture IDs: ARCH-0005

## Objective

Give managers a previewed share flow and visitors a focused read-only grid.

## Scope

Add Share links in Dataset Access for permitted managers. Support field selection, base filter, preview, copy link, rotate and revoke. Add a standalone reader for unauthenticated visitors, reuse the read-only presentation where practical, and cover the feature in the EN/VI handbook.

## Inputs

- Dataset public share management and read contracts, current Access tab, grid presentation and confirm-delete conventions.

## Related Artifacts

- [Requirement](../../artifacts/REQ-0103-dataset-integrations-and-live-sharing.md)
- [Design](../../artifacts/DES-0009-dataset-integrations-and-live-sharing.md)
- [Architecture](../../artifacts/ARCH-0005-dataset-integrations-and-live-sharing.md)
- [Decision](../../decisions/DEC-0103-dataset-integration-and-sharing-boundaries.md)
- [Delivery plan](../../artifacts/PLAN-0021-dataset-integrations-and-live-sharing.md)

## Expected Outputs

Localized share controls, desktop and mobile visitor page, integration walkthrough, accessibility and error-state evidence.

## Implementation Notes

Use shadcn components and theme tokens. Manager preview uses the exact public projection. Render only the approved fields and read/navigation controls. Use the shared exact-name confirmation for revoke. Keep search and pagination inside the approved view.

## Constraints

- Follow the existing backend layers, permission checks, API envelope and error catalog. Use EN/VI locale parity, shared UI components and theme tokens where applicable.
- Review and QA precede approval to merge into develop. Recheck shared Dataset schema and export changes from PLAN-0020 at task start.

## Dependencies

- [TASK-0371](../done/TASK-0371-dataset-public-share-api.md). Start after this dependency integrates, or document an approved stack.

## Acceptance Criteria

- A permitted manager creates a limited link from Access and previews the same rows and columns that an incognito browser loads from the copied URL.
- The public page handles loading, no matches, unavailable access, and retry. Controls are keyboard accessible and the grid works at narrow widths in both themes and locales.
- A revoked or rotated link is rejected on the next request. An open or previously copied URL grants only read access to its configured view. The handbook documents the manager and visitor flows.

## Validation Plan

Run Playwright as manager and anonymous visitor, including share preview parity, keyboard, mobile, light and dark, revoke and rotation. Run locale parity, lint, build, and a cross-milestone smoke run against a live backend. Run the applicable repository and Factory checks and record review and QA evidence on the task PR.

## Assumptions

Use the v1 scope of REQ-0103 and the proposed interfaces in ARCH-0005.

## Open Questions

Confirm the predecessor contract and integration before promoting to todo.

## Activity Log

- 2026-11-22: Planned from the owner-approved scope and sequence.

## Handoff Notes

Use a dedicated task branch from current develop when implementation is requested. This plan does not authorize a release or merge.
