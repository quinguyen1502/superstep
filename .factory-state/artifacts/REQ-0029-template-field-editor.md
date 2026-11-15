# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0029
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Source: owner request on 2026-10-18, “Can you add editors that support a tag replacer for state fields in the node message config?”, and two additions sent while it was in progress: “Fix this breaking layout while you are at it” (a screenshot of the editor header, where the product name ran under the workflow name field) and “Also look at the Save, Run, ... buttons: the text keeps sitting off the icon.”

## Summary

Node fields that take a `{{state.field}}` template get an editor that shows each state reference as a tag, suggests state fields while typing, and inserts a field from a menu.

## Problem Or Opportunity

- Prompt, query, URL, body, and MCP argument fields are plain text boxes. The author has to remember the field names and type `{{state.field}}` by hand.
- A typo such as `{{state.mesage}}` renders as an empty string at run time, with no warning in the editor.

## Scope

### In Scope

- One shared template editor for: LLM prompt, Human prompt, HTTP Tool URL and body, Retriever query, and MCP tool arguments
- State references shown as tags; references to a field that is not in the state schema are marked
- Suggestions after typing `{{`, and an insert-field menu
- Single-line mode for the URL and MCP arguments
- Editor header: the product name never runs under the workflow name field, and the header does not overflow down to 768px
- Small (`sm`) buttons: the icon lines up with the label

### Out Of Scope

- New template syntax (filters, nested paths, expressions)
- Backend changes; the stored value stays the same text
- Fields that the backend does not render (approval target, approvers, condition default)

## Stakeholders Or Users

- Workflow authors

## Desired Behavior

- The stored value is unchanged text: `Hello {{state.message}}` stays `Hello {{state.message}}`.
- Each `{{state.x}}` shows as a tag with the field name. Backspace or Delete removes a whole tag. Copy keeps the template text.
- A tag whose field is not in the state schema uses the destructive colour and says so in its tooltip.
- Typing `{{` opens a list of state fields with their types; choosing one inserts `{{state.x}}`.
- A button in the editor opens the same list and inserts at the cursor.
- Single-line fields turn pasted line breaks into spaces.
- Read-only for viewers, as the other inputs in the panel.

## Business Rules

- shadcn components and theme tokens only. Every new string in `en.json` and `vi.json`.

## Constraints

- No new dependency outside the CodeMirror packages already installed.
- No API or schema change.

## Acceptance Criteria

- In an LLM node, typing `{{` in the prompt lists the state fields; choosing `message` stores `{{state.message}}` and shows a `message` tag.
- The insert-field button inserts a field at the cursor.
- `{{state.missing}}` shows a marked tag when `missing` is not a state field.
- Saving and reloading keeps the exact template text.
- Viewers cannot edit the template fields.
- From 768px to 1600px the editor header has no horizontal overflow and nothing in it overlaps; the back button and logo stay visible.
- In `sm` buttons with a label, the icon centre is within 0.5px of the capital-letter centre.
- Existing Playwright specs pass after updating selectors for the new editor.

## Edge Cases

- Spaces inside the braces (`{{ state.x }}`) are a reference, as in the backend's `VAR_RE`.
- An empty state schema: the menu says there are no fields.

## Assumptions

- “Node message config” means the node fields that the backend renders with `{{state.field}}` (`engine/templating.py`).

## Open Questions

- None

## Related Artifacts

- Task: `.factory-state/tasks/done/TASK-0041-template-field-editor.md`
- Templating: `backend/app/engine/templating.py`
- UI conventions: `docs/ui-conventions.md`
