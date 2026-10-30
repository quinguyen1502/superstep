# Task

## Metadata

- Project: superstep
- Task ID: TASK-0147
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: none (owner request)
- Design IDs: none
- Architecture IDs: DEC-0008 (UI conventions)

## Objective

The canvas shows the run that is open in the Run panel. From the owner's screenshot on 2026-10-27 ("Tại sao node
"End" ko thấy mark done"): a Supervisor that called a workflow tool finished, the trace listed End, but the End node
on the canvas had no "done" badge.

Cause: the canvas marks came only from the live socket. A parent run waits for its workflow tool's child (TASK-0134),
the socket closes, and the worker runs the rest of the parent (the next model round, the agent's exit, End) on the
server. Opening that run (the panel's poll, or a history row) only turned "waiting" into "done" (TASK-0138), so the
steps after the wait never marked the canvas. Opening an older run also left the marks of the last live run.

## Scope

### In Scope

- `frontend/src/lib/run-marks.ts` (new): one function from run events to canvas marks (`_status`, `_dur`):
  - `markEvent` for one event (the live socket);
  - `markRun` for a whole run (opening a run), over cleared marks;
  - `canvasId` moves here from `components/editor/meta.ts`.
- `components/editor/use-studio.ts`: the socket and `openRun` both use it; the TASK-0138 patch goes away.
- `components/editor/canvas-nodes.tsx`: the node carries `data-status` for tests.

### Out Of Scope

- A live socket for the server part of a parent run: the panel's 2-second poll already opens the run once it moves on.

## Inputs

- The owner's screenshot of the Support team run.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0073-agent-workflow-tools.md`
- Design: none
- Architecture: none
- Decisions: `docs/ui-conventions.md` (DEC-0008)
- Discovery: none

## Expected Outputs

- After a run that waited for a child ends, every node it ran is "done" on the canvas, End included.
- Opening any run from history shows that run's marks.

## Implementation Notes

- Live behaviour is unchanged: the same rules (started, waiting, finished with the duration of the canvas node's own
  step, error, cancel and timeout) now live in one place.

## Constraints

- shadcn/ui and theme tokens only.

## Dependencies

- None.

## Acceptance Criteria

- In the Support team template run, Start, Supervisor and End are all "done" once the run finishes.
- A parent waiting for its child's approval shows the Agent node "waiting" and End without a mark.
- After the approval, the parent's End is "done" without reloading the page.
- Opening another run replaces the canvas marks.

## Validation Plan

- `cd frontend && npm run lint && npx tsc -b && npm run lint:ui -- --strict && npx vitest run`
- `npx playwright test e2e/workflow-tools.spec.ts` plus the studio specs that run workflows.

## Assumptions

- None.

## Open Questions

- None.

## Activity Log

- 2026-10-27: asked for by the owner ("Sửa đi: canvas tô trạng thái từ events của run khi mở run, dùng chung với
  luồng live") and fixed on `factory/task-0147-canvas-run-status`.
- 2026-10-27: merged into develop (PR #198) with the owner's approval; moved to done in TASK-0148's PR, which
  makes this move part of the task PR from now on.

## Handoff Notes

- Review: one pure module replaces the socket's five inline rules and the TASK-0138 patch; lint, `tsc -b`,
  `lint:ui --strict` and vitest (123, 6 new in `run-marks.test.ts`) pass.
- QA: `e2e/workflow-tools.spec.ts` 6 passed (en and vi): the live runs and the template run end with Start, the Agent
  node and End "done"; the waiting parent shows the Agent node "waiting" and End unmarked, then all "done" after the
  approval without a reload. Studio specs (hitl, runtime, trace, studio, time-travel, subgraphs, agent-node, foreach)
  18 passed. Screenshot `workflow-tool-template-canvas-en.png` shows the three nodes done.
- Not changed: an Agent node's duration on the canvas is its first step's, as before.
