# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0035
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Source: owner question "does langgraph support a Loop node?" and the reply "OK, build that too" (2026-10-19)

## Summary

A For each node runs a branch of the canvas once for every item of a list field.

## Problem Or Opportunity

- A loop over a list could only be built by hand from a Condition, a counter field and a tool that picks the next item.
- LangGraph supports cycles and `Send` fan-out, but the studio had no node for "repeat for each item".

## Scope

### In Scope

- Node type `foreach`: validation, compilation, run-time behaviour, the editor (palette, config panel, edge roles), docs, tests

### Out Of Scope

- Parallel items (`Send` fan-out). See DEC-0038.
- A body that is a separate saved workflow (a Subgraph node inside the body already gives this).

## Stakeholders Or Users

- Workflow authors

## Desired Behavior

- See DEC-0038.

## Business Rules

- The list field must be of type list. The item field and the optional index field must use the `replace` reducer. The index field must be an integer or number field. The three fields must differ.
- Exactly one `each` edge and one `done` edge. The `each` branch must lead back to the For each node.
- `max_items` is 1–1000 (default 100). A longer list fails the node at run time.

## Constraints

- Engine imports core only (DEC-0009). No new dependency. No new API error code (validation errors go through `WORKFLOW_INVALID`; run-time errors are node errors).

## Acceptance Criteria

- Items `["a", "b", "c"]` run the body three times in order; the fourth visit follows `done`. An `append` list collects one result per item. The run output does not contain the internal loop position.
- An empty or missing list follows `done` at once. A non-list value or more items than `max_items` is a node error.
- A loop of 60 items with a two-node body finishes (more steps than `STUDIO_RECURSION_LIMIT`).
- Each item gets its own idempotency key.
- A Human node inside the body pauses for the first item; resuming continues with the second item.
- Nested loops work, and the inner list restarts for every outer item.
- A cycle through a For each node needs no Condition.
- Validation names each rule above.
- Editor: the first edge drawn from a For each node is labelled `each`, the second `done`; selecting such an edge shows a role picker instead of a free-text label; the node panel lists only fitting fields.

## Edge Cases

- The list is read on every visit, so a body that changes the list changes what is left.
- The internal position goes back to 0 when the loop finishes, so an enclosing loop starts the list again.

## Assumptions

- Sequential items are enough for the first version; parallel items can follow as an option.

## Open Questions

- None

## Related Artifacts

- Decision: `.factory-state/decisions/DEC-0038-foreach-node.md`
- Task: `.factory-state/tasks/done/TASK-0049-foreach-node.md`
