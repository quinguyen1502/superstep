# Task

## Metadata

- Project: superstep
- Task ID: TASK-0126
- Status: done
- 2026-10-26: PR #160 merged into develop (9a4b79e) with the owner's approval after CI passed (15 passed, 2 skipped); moved to done.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: REQ-0072 (Agent node), REQ-0007 (Retriever node), REQ-0015 (template library)
- Design IDs: none
- Architecture IDs: DEC-0008 (UI conventions)

## Objective

Two small UI fixes the owner approved in chat on 2026-10-26 ("Làm đi"):

1. The Vietnamese label of `field.function` was still "Function" (the Tool node's function picker and the Agent
   node's built-in tool).
2. A workflow made from the Support agent or RAG template could not run, and nothing said why until Run
   (`WORKFLOW_INVALID`: "choose a knowledge base"). TASK-0122 noted this when it recorded the intro video.

## Changes

- `vi.json`: `field.function` is "Hàm"; it leaves the list of keys allowed to match English
  (`locales.test.ts`).
- A red hint under the knowledge base picker while none is chosen, on the Retriever node and on an Agent node's
  knowledge base tool (`editor.retrieverRequired`, en + vi).
- The template gallery passes the errors that `POST /api/templates/{id}/use` already returns to the editor, which
  lists them in the Run panel once, as a save does (router state, cleared after it is read).
- `editor.errorsTitle` / `editor.errorsBadge` get singular forms ("1 error to fix", not "1 errors").

## Acceptance Criteria

- In Vietnamese, the function picker's label is "Hàm".
- A workflow made from the RAG or Support agent template opens with the list of what it still needs, and the
  knowledge base picker shows the hint until one is chosen.
- A template that needs nothing (Router) opens without a list; a reload does not show the list again.

## Validation

- Frontend: `tsc -b`, `vitest`, e2e `templates`, `agent-tests`.
- Checked in the browser (en and vi): Support agent and RAG templates.

## Validation Results

- Frontend `tsc -b`: OK. `vitest`: 22 files, 105 tests passed.
- e2e `templates`, `agent-tests`, `i18n`: 6 passed. New checks:
  - the RAG template opens with "1 lỗi cần sửa" and the Retriever hint, and a reload clears the list;
  - the Router template opens with no list;
  - the Support agent's knowledge base tool shows the hint, and the built-in tool's label is "Hàm".
- Browser check on a local dev server (en and vi): Support agent and RAG from the gallery.
- Handbook `guide/templates.md` (en, vi) and CHANGELOG (Unreleased) updated.

## Review And QA

- Review: REV-0114, QA: QA-0114. Both were written after the merge, by TASK-0129 on 2026-10-26: the PR was merged on CI and the
  validation above, without them.
