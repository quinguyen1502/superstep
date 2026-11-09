# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0031
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-18
- Updated: 2026-10-18
- Source: remaining-work report of 2026-10-18 (item 8: "Template: only `{{state.field}}`, no filters or nested paths yet") and the owner's reply, "Except 2, 3, 4. Do the rest"

## Summary

Node templates read nested values (`{{state.order.items.0.sku}}`) and apply filters (`{{state.name | trim | upper}}`). The editor suggests filters, shows the chain on the tag, marks bad filters, and lets the author edit a tag as text.

## Problem Or Opportunity

- A nested value or a small transformation needed an extra Tool node.
- The tags created by TASK-0041 could not be edited; changing one meant deleting it and typing it again.

## Scope

### In Scope

- Backend parser, renderer, and validator (DEC-0034)
- Frontend parser, tags, filter completion, and double-click editing
- README in both languages

### Out Of Scope

- Loops, conditions, expressions, user-defined filters

## Stakeholders Or Users

- Workflow authors

## Desired Behavior

- See DEC-0034.

## Business Rules

- New error codes go in `CATALOG`, `docs/api-errors.md`, and both locale files.

## Constraints

- Existing `{{state.x}}` templates render as before, except that a `None` value now renders as an empty string.
- No new dependency.

## Acceptance Criteria

- `{{state.order.id}}`, `{{state.tags | join(", ")}}`, `{{state.x | default("n/a")}}` and the other listed filters render as documented. An exact MCP argument reference keeps the filtered type.
- The validator reports an unknown filter or a wrong argument in any template field. A run refuses it with `TEMPLATE_REF_INVALID`.
- Typing `|` inside a reference lists the filters. A tag shows `field.path | filter`. A bad filter makes the tag red.
- Double-clicking a tag shows its text; once the cursor leaves, it is a tag again.
- Backend and frontend parse the shared cases the same way.

## Edge Cases

- A path step on a non-container value, or an index out of range, gives an empty value.
- Text that is not valid syntax, such as `{{state.a | }}`, stays as literal text.

## Assumptions

- The filter set in DEC-0034 is enough for now.

## Open Questions

- None

## Related Artifacts

- Decision: `.factory-state/decisions/DEC-0034-template-paths-filters.md`
- Task: `.factory-state/tasks/done/TASK-0044-template-paths-filters.md`
