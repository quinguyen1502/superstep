# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0077
- Status: Done on 2026-10-30. Accepted on 2026-10-27 with the CLAR-0008 answers; planned as DEC-0072 and TASK-0174 to TASK-0178, all merged into develop.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-30
- Source: owner request in chat on 2026-10-27 ("3 hướng có thể làm thì bạn viết REQ trước đi"). REQ-0048 and
  REQ-0074 left attachments for a later phase, and `chat_turns.attachments` is reserved for them.

## Summary

- A person who chats with a workflow can attach files to a message: documents and images (CLAR-0008 question 1).
- The workflow receives them in a state field that the chat settings name. LLM and Agent nodes can read them:
  - a document's text, extracted as the knowledge bases already do;
  - an image, for models that can see images.
- Builders choose per chat whether attachments are allowed, and the limits apply.

## Owner Decisions

The owner answered CLAR-0008 on 2026-10-27 with the recommended option for every question ("Trả lời CLAR-0006 đến
CLAR-0009 theo đề xuất, rồi merge #200").

1. **Kinds**: documents (`.txt`, `.md`, `.pdf`, `.csv`) and images (PNG, JPEG, WebP).
2. **Workflow view**: a list field of file records. LLM and Agent nodes include the files only with "Include
   attachments" on. A model that cannot see images gets a note in place of the image, and the chat goes on.
3. **Storage**: in the database, as the chat logo is.
4. **Limits**: 10 MB per file and 5 files per message by default. A chat can lower them, and the operator sets the
   ceiling.
5. **Channels**: not now. Slack and Telegram files stay out of scope.
6. **Checks**: the type is read from the bytes, and files are served only as downloads with `nosniff`. No virus
   scanner.

## Problem Or Opportunity

- Many chat uses start from a file: "summarise this contract", "what does this invoice say", "is this screenshot an
  error". Today a person must paste the text, and images cannot be sent at all.
- The chat model already has room for this. `chat_turns.attachments` is reserved (DEC-0052), and REQ-0048 calls it
  phase 3.
- The pieces exist:
  - text extraction for `.txt`, `.md` and `.pdf` (`engine/documents.py`, used by knowledge bases);
  - binary storage in the database, as for the chat logo (`chat_logos`, TASK-0145);
  - the public chat's limits (REQ-0074).
- Dify, Flowise and Langflow all accept files in their chat pages, and Dify also accepts images for vision models.

## Scope

### In Scope

- **Allowing attachments**: a per-chat setting in Chat settings, off by default. It covers:
  - the allowed kinds: documents, images, or both (CLAR-0008 question 1);
  - the number of files and the size per file, 5 and 10 MB by default, under the operator's ceiling (CLAR-0008
    question 4);
  - the state field the files go to.
- **Attaching**:
  - an attach button and drag-and-drop in the composer of the public page, the embed and the studio Chat tab;
  - each file shows as a chip with its name, size and a remove button;
  - images show a thumbnail.
- **Storage** in the database, as the chat logo is (CLAR-0008 question 3). A file belongs to its turn. Retention deletes it with its session.
- **The type** is read from the file's bytes, not from its name or the browser's type, as the logo does. A file whose
  type is not allowed is refused with a `CHAT_ATTACHMENT_*` code.
- **How the workflow sees the files** (CLAR-0008 question 2):
  - a list field of `{id, name, type, size, text?}`;
  - documents get their extracted text, capped in length;
  - images are passed to a model as images when the LLM or Agent node turns on "Include attachments".
- **Models**:
  - for providers that support images (OpenAI, Anthropic, OpenRouter, OpenAI-compatible with vision), image parts in
    the messages;
  - for a model without vision, the image is replaced by a note that the model reads, and the run goes on (CLAR-0008
    question 2).
  - The mock model describes the files it got, so demos and tests work offline.
- **Showing the files**:
  - the turn shows its attachments;
  - only the session's owner can download them, and the builder can from the Visitors list;
  - a file is always served as a download with `nosniff`, never inline as HTML.
- **Limits**: the size and count limits, plus the visitor limits of REQ-0074. An upload counts as a message for the
  rate limits.
- Errors in CATALOG, `docs/api-errors.md` and both locales. en and vi strings. Handbook en and vi. CHANGELOG. A
  decision record for storage and the state shape.
- Tests:
  - pytest: types by bytes, limits, isolation between visitors, retention, extraction, image parts per provider with
    stubs;
  - vitest;
  - e2e: attach a PDF and an image on the public page, and the mock answer mentions them, in vi and en.

### Out Of Scope

- Files in Slack and Telegram chats (CLAR-0008 question 5).
- Audio, video and Office files (`.docx`, `.xlsx`), unless CLAR-0008 question 1 adds them.
- Virus scanning by an external engine (CLAR-0008 question 6).
- Files produced by the workflow and sent back to the person.
- Adding chat files to a knowledge base.

## Stakeholders Or Users

- Visitors and studio users who chat with a workflow.
- Builders who decide what may be uploaded.
- The deployment's operator, who stores the files and pays for model calls.

## Current Context

- `chat_turns.attachments` (Text, JSON) is reserved and unused.
- `engine/documents.py`: `EXTENSIONS = (".txt", ".md", ".pdf")`, with `pypdf` for PDFs.
- The chat logo's bytes are stored in `chat_logos`, typed by magic bytes, and served with `nosniff` (TASK-0145).
- LLM calls send text messages only. Providers build LangChain chat models, and Anthropic is called over HTTP
  (DEC-0063 decision 4).
- The vision lists a "public multi-tenant SaaS" as a non-goal. The limits here protect one self-hosted deployment.

## Desired Behavior

1. The builder turns on attachments in Chat settings for documents and images, keeps the default limits, and names
   the field `files`. Their LLM node turns on "Include attachments".
2. A visitor drags a PDF into the composer, types "Summarise this", and sends. The answer summarises the PDF. The turn
   shows the PDF's chip, and the visitor can download it again.
3. A visitor attaches a 30 MB file. The page refuses it before uploading and says what the limit is.
4. The builder turns attachments off. The attach button disappears, and an upload from a page that is already open is
   refused.

## Business Rules

- Only the session's owner can attach to it or download its files. The builder can download from the Visitors list.
- A file is accepted only if its kind is allowed for that chat and its bytes match that kind.
- Extracted text is capped (for example 50,000 characters per file) and marked as cut when it is longer.
- Files never reach a node that did not turn on "Include attachments", except as the state field's metadata.
- Attachments are refused in demo mode (`STUDIO_DEMO_MODE`).

## Constraints

- The layers of DEC-0009 apply. Migrations go through Alembic.
- shadcn/ui and theme tokens only. en and vi have the same keys.
- No new heavy dependency. `pypdf` is already there. Images are not re-encoded on the server.
- Request bodies stay bounded (`limit_body`), so an upload cannot bypass the size limit.

## Acceptance Criteria

- With attachments on, a visitor sends a PDF and an image in one message. The workflow's field lists both, with the
  PDF's text. The mock model's answer names both.
- A file renamed to `.pdf` whose bytes are not a PDF is refused with a `CHAT_ATTACHMENT_*` code.
- A second visitor cannot download the first visitor's file. A guessed file id returns not found.
- An image sent to a model without vision reaches it as a note, and the run goes on.
- Retention deletes the session's files. The table holds no orphan files after the cleanup.
- With attachments off, the API refuses uploads and the composer has no attach button.
- The backend suite, `tests/test_layers.py`, `tests/test_api_envelope.py`, vitest, e2e and the strict handbook build
  pass.

## Edge Cases

- A PDF with no text layer, such as a scan: its text is empty, and the field says so. There is no OCR.
- An encrypted PDF: it is refused, or its text is empty with a note.
- The person removes a file before sending. It is never stored.
- An upload is in progress when the person sends the message. The message waits for the upload or refuses to send.
- Two files with the same name are both kept, with different ids.
- A Human node asks a question. Answering it in the chat takes text only, not files.

## Assumptions

- Files are small: documents and screenshots, not datasets.

## Open Questions

None. CLAR-0008 is answered.

## Planned Tasks

Planned on 2026-10-30. The layout is DEC-0072. The owner confirmed the set and DEC-0072 on 2026-10-30.

- TASK-0174 Storage, upload and download routes, type checks, limits, retention.
- TASK-0175 Chat settings and the workflow list field.
- TASK-0176 "Include attachments" on LLM and Agent nodes, image parts, vision note, mock.
- TASK-0177 Composer, settings and Visitors list UI (en, vi).
- TASK-0178 Handbook (en, vi), API errors, Playwright e2e, CHANGELOG.

## Related Artifacts

- `.factory-state/artifacts/CLAR-0008-chat-attachments.md`
- `.factory-state/artifacts/REQ-0048-agent-chat.md`, `.factory-state/artifacts/REQ-0074-public-chat-page.md`
- `.factory-state/decisions/DEC-0052-web-chat-model.md`, `.factory-state/decisions/DEC-0067-public-chat-page.md`
- `.factory-state/decisions/DEC-0063-agent-node-expansion.md` (providers)
- `docs/ui-conventions.md`, `docs/backend-architecture.md`
