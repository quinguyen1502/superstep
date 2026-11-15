# Task

## Metadata

- Project: superstep
- Task ID: TASK-0072
- Status: done (PR #96, REV-0067, QA-0067)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-22
- Updated: 2026-10-22
- Requirement IDs: REQ-0043
- Design IDs: none
- Architecture IDs: DEC-0045

## Objective

Document Export to Python in the handbook (en, vi) as a learning page: how each canvas part is written in LangGraph,
and how to run the file.

## Scope

### In Scope

- New page `handbook/docs/{en,vi}/guide/python-export.md` in the Guide section (nav in `mkdocs.yml` and
  `mkdocs.vi.yml`):
  - what the panel shows, Copy and Download;
  - the canvas → code table (from DEC-0045), with a short code excerpt for state and reducers, a condition, a Human
    `interrupt` and a subgraph;
  - running the file: `pip install langgraph`, the mock by default, environment variables and packages for a real
    model; what is not included (credentials, studio extras, stubs for Retriever, MCP and Send email);
  - limits: imported repositories, timeouts.
- Screenshot `code-tab.png` (en, vi; named after the Code tab) from `frontend/e2e/handbook.spec.ts`; only the images this task changes are
  committed.
- Links from the editor page, the Guide index and the quickstart's "Next steps"; the API reference already lists the
  route (TASK-0070).
- README feature list: one line.

### Out Of Scope

- A tutorial on LangGraph beyond what the exported file shows.

## Inputs

- TASK-0070, TASK-0071, DEC-0045.
- `handbook/docs/{en,vi}/`, `mkdocs.yml`, `mkdocs.vi.yml`, `frontend/e2e/handbook.spec.ts`, `check_images.py`.

## Related Artifacts

- Requirement: `.factory-state/artifacts/REQ-0043-python-export.md`
- Design: none
- Architecture: DEC-0045
- Discovery: the handbook capture re-renders every image (TASK-0069 handoff).
- Clarifications: none

## Expected Outputs

- Handbook page (en, vi), screenshot, links, README line

## Implementation Notes

- Code excerpts come from a real export of a built-in template, so they match what users see.

## Constraints

- en and vi pages with the same structure (CI checks it); strict builds and the image check pass.

## Dependencies

- TASK-0070 and TASK-0071.

## Acceptance Criteria

- The page (en, vi) covers the scope above with a screenshot; both strict builds, the same-pages check and
  `check_images.py` pass.
- E2E (handbook capture) passes.

## Validation Plan

- `zensical build -f mkdocs.yml --strict`, `-f mkdocs.vi.yml --strict`, `check_images.py site`;
  `HANDBOOK_SHOTS=1 npx playwright test handbook`.

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-22: planned from REQ-0043.
- 2026-10-22: started after PR #94 merged (owner approved).
- 2026-10-22: implemented. Review REV-0067, QA QA-0067. The approval select's missing key is fixed by PR #95
  (TASK-0073); the screenshot is retaken after it merges.
- 2026-10-22: PR #95 merged (owner approved the order); rebased, `code-tab.png` (en, vi) retaken: the select shows
  "not connected" (and its vi label). Owner approved; done.

## Handoff Notes

- None.
