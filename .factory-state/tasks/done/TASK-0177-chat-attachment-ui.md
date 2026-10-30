# Task

## Metadata

- Project: superstep
- Task ID: TASK-0177
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0077
- Design IDs: none
- Architecture IDs: DEC-0072

## Objective

Add attachment controls to the chat composer (public page, embed, studio Chat tab), to Chat settings, and to the Visitors list.

## Scope

### In Scope

- Composer: attach button and drag-and-drop, file chips with name, size and remove; image thumbnails (object URLs); pre-upload checks of kind, size and count with the configured limits; send waits for uploads in progress.
- Turns show their attachments with download links.
- Chat settings: switch, kinds, max files, max size (bounded by the operator ceiling from the settings response), field name.
- Visitors list: builder can download a visitor's files.
- LLM and Agent node Config: "Include attachments" switch.
- en and vi strings with the same keys; shadcn components and theme tokens only.
- vitest for the chips, the checks and the settings form.

### Out Of Scope

- Backend (TASK-0174 to TASK-0176).
- Handbook and e2e (TASK-0178).

## Inputs

- REQ-0077 'Attaching', 'Showing the files'; `docs/ui-conventions.md`.
- Public chat page and Chat tab components from REQ-0074 / TASK-0140 to TASK-0145.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0077-chat-attachments.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0072-chat-attachments.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0008-chat-attachments.md`

## Expected Outputs

- Visitors and builders can attach, see and download files.

## Implementation Notes

- Reuse the composer shared by the public page and the Chat tab so both get the feature once.

## Constraints

- Layers of DEC-0009: routes call services, services call repositories, no FastAPI in a service, no SQLAlchemy in a route. `tests/test_layers.py` passes.
- Every API error uses the common envelope with an English error code listed in `core/errors.py` CATALOG, `docs/api-errors.md`, and `frontend/src/locales/en.json` and `vi.json`. `tests/test_api_envelope.py` passes.
- UI uses shadcn/ui components and theme tokens only. en and vi locale files keep the same keys.
- Schema changes go through a new Alembic revision after the latest one on `develop` at branch time.
- No new heavy dependency.

## Dependencies

- TASK-0175 (API); TASK-0176 for the node switch.

## Acceptance Criteria

- With attachments off the composer has no attach button.
- A 30 MB file is refused in the page with the limit in the message, before upload.
- Chips, thumbnails and removal work; vitest passes; lint and build pass.
- en and vi keys match.

## Validation Plan

- `cd frontend && npm run lint && npm test && npm run build`

## Assumptions

- The designer step is skipped. REQ-0077 and its CLAR already describe the screens.

## Open Questions

- None. DEC-0072 is accepted.

## Activity Log

- 2026-10-30: planned from REQ-0077 (DEC-0072). Status todo. Not started.
- 2026-10-30: owner confirmed the task set and accepted the decision record.
- 2026-10-30: implemented on `factory/task-0177-chat-attachment-ui` from `develop`. Composer attach button, drag-and-drop, pre-upload checks, chips with thumbnails and remove; turns list files with downloads (fetch + blob, so the widget's visitor header is sent); Chat settings Attachments section bounded by the server ceiling; Visitors downloads; Include attachments switch on LLM and Agent nodes; the page settings expose the limits. `factory verify run --profile full` passed. The owner authorized the merge of the REQ-0077/REQ-0078 task PRs. Moved to done on this PR before the merge (TASK-0148).

## Handoff Notes

- Branch `factory/task-0177-chat-attachment-ui` from `develop`.
- Review: `.factory-state/artifacts/REV-0153-task-0177.md`. QA: `.factory-state/artifacts/QA-0153-task-0177.md`.
