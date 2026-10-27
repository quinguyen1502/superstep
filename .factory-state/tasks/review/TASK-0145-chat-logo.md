# Task

## Metadata

- Project: superstep
- Task ID: TASK-0145
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0074
- Design IDs: none
- Architecture IDs: DEC-0067 (decision 10)

## Objective

Let the builder upload a logo for a published chat, and give a chat without one a default look: the title's first
letter and a built-in picture. Owner request on 2026-10-27 ("trong chatbot, có thể cho user upload logo và tạo 1
default illustration"; "Ok, làm TASK-0145 theo đề xuất, đưa vào 0.9.0").

## Scope

### In Scope

- Backend:
  - the `chat_logos` table and migration `0041_chat_logos`;
  - `logo` in the Chat settings: a `data:` URL sets it, `""` removes it, the current hash keeps it;
  - the type is read from the bytes (PNG, JPEG, WebP), at most 256 KB, no SVG;
  - `GET /api/public/chat/{slug}/logo` and `GET /api/workflows/{wid}/chat/logo`;
  - `CHAT_LOGO_INVALID` and `CHAT_LOGO_NOT_FOUND`.
- Frontend:
  - the Logo row in the publish settings (upload, change, remove, preview);
  - on `/c/{slug}`: the logo in the header, over the welcome and as the tab's icon;
  - without a logo, the first letter and the picture;
  - the logo is a square with rounded corners, and the welcome block is centred (the owner's review);
  - the widget's bubble keeps its chat icon (the owner's review).
- Tests (pytest, vitest, e2e), handbook en and vi, API reference, CHANGELOG, REQ-0074 and DEC-0067.

### Out Of Scope

- Custom colours and custom domains. An AI-made picture.

## Inputs

- TASK-0140 to TASK-0144 (PRs #186 to #190).

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0074-public-chat-page.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0067-public-chat-page.md` (decision 10)
- Decisions: none
- Discovery: none
- Clarifications: `.factory-state/artifacts/CLAR-0005-public-chat-page.md` (question 6 kept the page plain; the owner
  added the logo afterwards)

## Expected Outputs

- A published chat shows its logo on the page and in the tab. A chat without one still looks finished.

## Implementation Notes

- The logo travels with Save in the settings `PUT`, so the dialog stays one form. Removing it is a field change, not
  a delete feature with a typed confirmation.
- The settings keep only the hash. The address `?v=<hash>` changes with the image, so it can be cached for good.

## Constraints

- shadcn/ui and theme tokens only. The picture is inline SVG with token classes, so it follows light and dark.

## Dependencies

- TASK-0144.

## Acceptance Criteria

- An SVG, a GIF, a file over 256 KB or text that is not base64 is refused with `CHAT_LOGO_INVALID`. The type comes
  from the bytes, not the `data:` URL.
- A visitor gets the logo only while the chat is published. The builder sees it either way. Removing it gives
  `CHAT_LOGO_NOT_FOUND`.
- The page shows the logo in the header, over the welcome and in the tab, also inside the widget's frame. Without one
  it shows the first letter and the picture.
- pytest, vitest and the chat e2e specs pass. The handbook builds in strict mode.

## Validation Plan

- `cd backend && .venv/bin/python -m pytest -q`
- `cd frontend && npm run lint && npm run build && npx vitest run`
- `npx playwright test e2e/public-chat.spec.ts e2e/chat-embed.spec.ts e2e/agent-chat.spec.ts`
- handbook strict build

## Assumptions

- 256 KB is enough for a logo. The nginx body limit is 10 MB.

## Open Questions

- None.

## Activity Log

- 2026-10-27: asked for by the owner and planned; implemented on `factory/task-0145-chat-logo`, stacked on TASK-0144.

## Handoff Notes

- Review REV-0128, QA QA-0128.
