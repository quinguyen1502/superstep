# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0072
- Status: Accepted. The owner approved the decisions and the task set (TASK-0174 to TASK-0178) on 2026-10-30, with decision 4 as recommended.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Related Requirements: REQ-0077 (CLAR-0008)
- Related Architecture: DEC-0009 (layers), DEC-0010 (envelope and error codes), DEC-0052 (web chat model), DEC-0067 (public chat page), DEC-0063 (providers), DEC-0008 (UI conventions), DEC-0033 (branches from `develop`)
- Related Tasks: TASK-0174, TASK-0175, TASK-0176, TASK-0177, TASK-0178

## Context

- CLAR-0008 fixed the kinds, the workflow view, database storage, the limits, the channels and the checks.
- `chat_turns.attachments` (Text, JSON) is reserved and unused. The chat logo stores bytes in its own table and checks magic bytes (TASK-0145).
- `engine/documents.py` extracts `.txt`, `.md` and `.pdf` text with `pypdf`.
- LLM calls send text only. Run state is checkpointed, so large values in state are copied on every step.

## Decision

1. **Storage.** A new table `chat_attachments` holds bytes, kind, MIME, size, extracted text and the session and turn ids. `chat_turns.attachments` stores only the ordered list of attachment ids. Upload happens before send (one file per request); an unsent upload belongs to the session and is swept after one hour.
2. **State shape.** The configured field is a list of `{id, name, type, size, text?, text_cut?}`. Image bytes never enter the run state or checkpoints; the engine reads them through a port when an LLM or Agent node with "Include attachments" builds its messages.
3. **Limits.** Defaults 10 MB and 5 files per message; per-chat values may only lower them; operator ceilings `STUDIO_CHAT_ATTACHMENT_MAX_MB` and `STUDIO_CHAT_ATTACHMENT_MAX_FILES`. The request body limit is enforced while reading.
4. **Exports.** Exported Python, LangGraph project and TypeScript code accept the same field and include document text when "Include attachments" is on; image parts are included when the file record carries a `data_url` supplied by the caller. REQ-0077 did not mention exports; the owner chose this on 2026-10-30.
5. **Vision capability.** A per-provider flag plus a per-model allow list in `engine/providers.py`; unknown models count as text only and get the note.

## Rationale

- Separate bytes keep session listing and checkpoints small.
- Upload-before-send gives the page progress and refusal before the message exists, and matches the chip UI.

## Alternatives Considered

- Base64 files inside the WebSocket message: simpler, but the message can exceed the WebSocket frame limits and ties the upload to the send. Not chosen.
- Bytes in the run state: makes exports trivial but bloats every checkpoint. Not chosen.
- Exports ignore attachments: least work, but an exported workflow behaves differently from the studio. Not chosen.

## Impacts

- New table and Alembic revision, new routes under the public chat and studio chat prefixes, new `CHAT_ATTACHMENT*` error codes, new settings fields, a node setting on LLM and Agent nodes.

## Risks

- Database growth on busy deployments; mitigated by limits, retention and the operator ceilings.
- Provider image formats drift; covered by stub tests per provider.

## Approval

- Approved By: Thái Quí Nguyễn
- Approved On: 2026-10-30
- Scope And Limits: The CLAR-0008 answers and decisions 1 to 5 as written. Decision 4 approved as recommended: exports take the same attachments field, include document text when "Include attachments" is on, and include images only when the caller supplies a `data_url`.

## Review Or Revisit Trigger

- Operators ask for volume or S3 storage, or Slack and Telegram files.
