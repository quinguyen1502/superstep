# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0065
- Status: Accepted
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Related Requirements: REQ-0045 (Vietnamese language quality)
- Related Architecture: DEC-0010 (API envelope and error codes)
- Related Tasks: TASK-0132

## Context

The static workflow checks (`engine/validator.py` and the node modules it calls) return English strings. The API sends
them as `errors`, and the editor showed them as they came, so a Vietnamese UI listed "Retriever node r: choose a
knowledge base" under "1 lỗi cần sửa" (REV-0114). API errors are already translated by code (`errors.<CODE>`,
DEC-0010), but these messages had no code. About 130 different messages come from twelve modules.

Options:

1. Match the English text in the frontend with patterns. Nothing changes in the backend, but the wording would live
   in two places and a changed message would silently stop being translated.
2. Translate in the backend by `Accept-Language`. UI strings would then live outside the locales.
3. Give each message a code and parameters in the backend, and translate by code in the frontend, like API errors.

## Decision

Option 3.

1. `engine/issues.py` holds `MESSAGES`, one English template per code, and `Issue`, a `str` subclass with `code` and
   `params`. Every check returns `Issue("CODE", **params)`. The text is the same as before, so every caller that reads
   the list as strings is unchanged: tests, SDKs, MCP, exports, logs.
2. The API keeps `errors` and adds `issues`, the codes in the same order (`{"code", "params"}`, or `null`). It does
   this in `POST /api/validate`, in workflow save, in template use, and in the run `error` event.
3. The frontend has `validation.<CODE>` in `en.json` and `vi.json`. `issueTexts()` in `lib/i18n.ts` uses the code
   when the locale knows it, and the English text otherwise.
4. `tests/test_validation_messages.py` keeps `en.json` equal to `MESSAGES`, `vi.json` on the same keys, and every
   code used in the engine in `MESSAGES`. `locales.test.ts` checks the Vietnamese against the glossary.
5. A message whose detail comes from a code checker (a Python syntax error, for example) gets the code `NODE_PROBLEM`.
   The node prefix is translated; the detail stays as the checker wrote it.

## Consequences

- A new check needs a `MESSAGES` entry and both locale strings. The backend test fails until they exist.
- Old clients that read only `errors` see no change.
- Runtime errors (`NODE_FAILED`, a node's exception text) are not covered. They are not validation messages.
