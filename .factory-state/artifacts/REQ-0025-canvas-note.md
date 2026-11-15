# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0025
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Source: owner request 2026-10-18, “add a note block on the flowchart.”

## Summary

The author can place a note on the canvas. The note is text for people reading the graph. The run never executes it.

## Problem Or Opportunity

The canvas only holds nodes that run. There is no place to leave a comment next to a branch or a tool.

## Scope

### In Scope

- A sticky on the flowchart, added by right-clicking the canvas. It is not a graph node in the palette or the command palette.
- Multiline plain text, shown on the sticky and edited on it while it is selected.
- The note is saved with the workflow and restored with it.
- Validation, compile, and Arrange treat the note as outside the executable graph.

### Out Of Scope

- Markdown rendering, colours per note, and resizing with a custom drag handle.
- Connecting a note to a node. Insert before, insert after, and insert on an edge do not offer a note.
- An executable comment, a subgraph called from a note, or a note inside an imported repository graph.
- Typed-name delete. Removing a note is the same canvas delete as removing any other node.

## Stakeholders Or Users

- Workflow authors documenting a graph for themselves or a teammate

## Current Context

- Node types in the editor are `start`, `llm`, `retriever`, `tool`, `mcp`, `condition`, `human`, `join`, `subgraph`, and `end`, plus imported `code`.
- `backend/app/engine/validator.py` rejects an unknown type and requires an outgoing edge from every node except End.
- `compile_workflow` adds every node to the `StateGraph`.
- Arrange (`frontend/src/lib/layout.ts`) places every node with dagre.
- DEC-0008 gives each node type `--node-<type>`, `--node-<type>-foreground`, and `--node-<type>-muted`. The canvas does not draw a left accent bar.
- Canvas delete does not use `ConfirmDeleteDialog`. That dialog is for persisted records.

## Desired Behavior

- The author right-clicks the canvas and chooses Add note. A sticky appears at that spot, with no connection handles and no node card.
- The block shows its text. Empty text shows a placeholder. Selecting the note edits the text. The text survives selecting another node and coming back, and it survives save and reload.
- A graph with Start → End plus a loose note validates and runs. The note does not appear in the trace.
- An edge whose source or target is a note fails validation, and the message names the note.
- Arrange moves the executable nodes and leaves each note where it was.
- Copy, paste, duplicate, and undo include the note and its text.

## Business Rules

- A note does not need an outgoing edge, and it must not have one.
- UI strings live in `en.json` and `vi.json` with the same keys.
- The note uses the three `--node-note*` tokens from DEC-0008. Status colours stay on `success`, `warning`, and `destructive`.

## Constraints

- The engine does not import FastAPI. No new API route and no new error code.
- shadcn components and theme tokens. No hard-coded colours.

## Acceptance Criteria

- Right-click on the canvas can add a sticky. The node palette, the command palette, insert before, insert after, and insert on an edge cannot.
- The note has no handles. Its text is still there after save and reload.
- A workflow with a loose note validates. Compile does not register the note as a graph node, and a run of Start → End does not emit an event for the note.
- An edge into the note fails validation and the message names the note.
- Arrange leaves the note's position unchanged.
- Deleting the note does not ask the author to type its name.

## Edge Cases

- A note with no text is valid.
- Several notes on one graph are all ignored by compile and Arrange.
- Pasted JSON that gives a note an edge fails validation rather than being dropped silently.

## Assumptions

- The note is plain text in `data.text`, not Markdown.
- Designer and architect are skipped. The owner asked for a sticky, added from the canvas context menu, rather than a node card (2026-10-18).
- `factory ready` does not exit 0 on this machine. The owner asked for the task anyway. Do not install packages to clear it.
- One task. Independent of REQ-0024.

## Open Questions

- None

## Related Artifacts

- Task: `.factory-state/tasks/done/TASK-0037-canvas-note.md`
- UI conventions: `docs/ui-conventions.md`
- Decision: `.factory-state/decisions/DEC-0008-shadcn-ui-and-theme-tokens-only.md`
- Validator: `backend/app/engine/validator.py`
- Compiler: `backend/app/engine/compiler.py`
