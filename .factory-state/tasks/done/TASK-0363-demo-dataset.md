# Task

## Metadata

- Project: superstep
- Task ID: TASK-0363
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-21
- Updated: 2026-11-21
- Requirement IDs: REQ-0061, REQ-0097, REQ-0101

## Objective

Give public demo visitors a populated Dataset grid for trying the read-only Studio experience.

## Scope

- Seed a synthetic support ticket dataset at demo startup, with enough rows for paging and varied fields for filtering, sorting, grouping, and summaries.
- Make the sample visible using existing team dataset access and the demo viewer role. Permit the Studio's read-only Dataset POST queries through the demo guard.
- Keep Dataset writes and workflow Dataset operations subject to the existing demo restrictions. Formula and relation fields and deployment are outside this task.

## Related Artifacts

- [Public demo](../../artifacts/REQ-0061-demo-mode.md)
- [Datasets](../../artifacts/REQ-0097-datasets.md)
- [Phase 3](../../artifacts/REQ-0101-datasets-phase-3.md)

## Acceptance Criteria

- Demo boot creates exactly one sample with 125 synthetic tickets and the same boot can run again without duplicating or replacing rows. Regular Studio startup creates no demo dataset.
- Existing and new demo visitors can open the sample, filter, sort and page rows, group by team and calculate summaries. An unrelated private dataset stays out of the list and is inaccessible to visitors.
- Demo visitors cannot write rows, change the schema, or run Dataset workflow operations. Their regular workflow samples remain available.
- The demo docs state what visitors can try.

## Validation Plan

- Run demo, Dataset API, and layer tests. Verify the public-style sign-in and sample query against a fresh local demo instance.

## Assumptions

- Use fictional support tickets so demos can reset and redisplay them without copying user data.
- Keep the public demo read-only. Promotion and deployment follow the normal approval process.

## Activity Log

- 2026-11-21: Opened from the owner's request for demo data.
- 2026-11-21: Implemented and validated the boot seed, viewer access, read-only queries, and CSV download. Moved to review.

- 2026-11-21: The owner approved merging PR #422 into develop. Marked done with local and reviewed-head QA complete. Final-head CI gates the squash merge.

## Review And QA

- [Review](../../artifacts/REV-0352-TASK-0363-demo-dataset.md)
- [QA report](../../artifacts/QA-0352-TASK-0363-demo-dataset.md)
