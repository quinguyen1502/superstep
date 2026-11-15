# Task

## Metadata

- Project: superstep
- Task ID: TASK-0361
- Title: Highlight key features in the README
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-15
- Updated: 2026-11-15
- Priority: P2
- Size: XS

## Objective

Make the main README highlight Datasets, observability, and the public schedule API and link readers to the relevant handbook pages.

## Acceptance Criteria

- Preserve the README headings and the existing three-image gallery layout.
- Describe Datasets, observability, public workflow schedules, and Python and TypeScript exports in Features.
- Show the current Dataset grid and the Usage dashboard in the gallery.
- Keep the README independent of specific release versions.

## Validation Plan

Check the README against the original outline and confirm the gallery image dimensions and handbook links. Compare the descriptions with the changelog and handbook. Run the Factory hygiene check and `git diff --check`.

## Related Artifacts

- [0.13.0 release preparation](../done/TASK-0360-release-0-13-0.md)

## Activity Log

- 2026-11-15: Updated the English README with the released highlights and durable feature descriptions. Reviewed against the published changelog and handbook. Confirmed all five new links and both handbook anchors. Factory hygiene and `git diff --check` passed.

- 2026-11-15: Updated the heading and changelog link following owner feedback. Confirmed the README contains no explicit release version and the changelog target exists. Factory hygiene and `git diff --check` passed.

- 2026-11-15: Followed owner feedback by removing the extra section and consolidating the copy under Features. Preserved the original headings and gallery layout. Captured the Dataset summary in Studio using isolated sample data and reused the handbook Usage screenshot. Verified gallery dimensions, handbook destinations, and Factory hygiene.

- 2026-11-15: The owner approved PR #420. Final review confirmed that the README preserves its original outline, the Features copy matches the handbook, and the gallery shows the described UI. QA confirmed all three PNGs have matching dimensions, the handbook links resolve, and Factory hygiene passes. Merge is gated on the final commit's CI.
