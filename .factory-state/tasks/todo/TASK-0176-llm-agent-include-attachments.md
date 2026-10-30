# Task

## Metadata

- Project: superstep
- Task ID: TASK-0176
- Status: todo
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Requirement IDs: REQ-0077
- Design IDs: none
- Architecture IDs: DEC-0072

## Objective

Add "Include attachments" to LLM and Agent nodes so documents reach the model as text and images as image parts, with a note for models that cannot see.

## Scope

### In Scope

- Node setting `include_attachments` (field name from the chat settings, overridable) on LLM and Agent nodes; validator checks the field exists.
- Message building in `engine/llm.py` / `engine/agents.py`: documents appended as labelled text blocks; images loaded through a port (the engine never reads the database directly) and sent as image parts.
- Per provider image parts: OpenAI, OpenRouter and OpenAI-compatible (`image_url` data URL), Anthropic HTTP (`image` base64 block). A `vision` capability flag per provider/model in `engine/providers.py`; unknown models count as no vision.
- No vision: the image becomes the note "An image named <name> was attached, but this model cannot see images." and the run goes on.
- The mock model names each file it received (kind and name) so demos and e2e work offline.
- Exports: per DEC-0072 decision 4.

### Out Of Scope

- Upload and storage (TASK-0174).
- UI (TASK-0177).

## Inputs

- REQ-0077 'Models'; DEC-0072 decisions 2 and 4.
- `engine/llm.py`, `engine/providers.py`, `engine/agents.py`, `engine/ports.py`, exporters.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0077-chat-attachments.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0072-chat-attachments.md`
- Decisions: `DEC-0009-layered-backend-sqlalchemy-alembic.md`, `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0008` (`docs/ui-conventions.md`), `DEC-0033` (task branches from `develop`)
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0008-chat-attachments.md`

## Expected Outputs

- LLM and Agent nodes send attachments when asked; stub tests per provider.

## Implementation Notes

- Keep images out of checkpoints: the state keeps ids only and the port reads bytes at call time.
- Nodes without the setting see only the field's metadata.

## Constraints

- Layers of DEC-0009: routes call services, services call repositories, no FastAPI in a service, no SQLAlchemy in a route. `tests/test_layers.py` passes.
- Every API error uses the common envelope with an English error code listed in `core/errors.py` CATALOG, `docs/api-errors.md`, and `frontend/src/locales/en.json` and `vi.json`. `tests/test_api_envelope.py` passes.
- UI uses shadcn/ui components and theme tokens only. en and vi locale files keep the same keys.
- Schema changes go through a new Alembic revision after the latest one on `develop` at branch time.
- No new heavy dependency.

## Dependencies

- TASK-0175.

## Acceptance Criteria

- A stub OpenAI and a stub Anthropic call receive one image part and the PDF text.
- A model without vision receives the note and the run finishes.
- The mock answer names both files.
- A node with the setting off gets no file content.
- Export snapshot tests pass.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd backend && .venv/bin/python -m pytest -q tests/test_layers.py tests/test_api_envelope.py`

## Assumptions

- The designer step is skipped. REQ-0077 and its CLAR already describe the screens.

## Open Questions

- None beyond those listed in DEC-0072.

## Activity Log

- 2026-10-30: planned from REQ-0077 (DEC-0072). Status todo. Not started; waits for the owner to confirm the task set.

## Handoff Notes

- Branch `factory/task-0176-llm-agent-include-attachments` from `develop`.
