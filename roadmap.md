# Roadmap

Phases accepted by the owner on 2026-10-16 (DEC-0007, supersedes the P0/P1/P2 bands of DEC-0004). Task IDs follow phase order; old IDs are mapped in `docs/factory-task-renumbering.md`.

## MVP baseline (done)

- REQ-0001 MVP baseline — implemented and verified (see DISC-0001)

## Phase 1 — Feasibility (login, workflow list, simple core)

Status as of 2026-10-17: all Phase 1 work is in `develop` (it was the base of the merged stack #11–#25). The original PRs #1 and #4–#10 still target `main`/stacked branches and stay open, because `main` is not touched.

| # | Task | Title | Status | PR | Branch base |
|---|---|---|---|---|---|
| 1 | TASK-0001 | Confirm project context and technical baseline | done (in `develop`) | (on `main`) | — |
| 2 | TASK-0002 | CI + Factory deps/verify unblock | done (in `develop`) | [#1](https://github.com/quinguyen1502/langgraph-studio/pull/1) | `main` |
| 3 | TASK-0003 | Harden auth/login and workflow list | done (in `develop`) | [#5](https://github.com/quinguyen1502/langgraph-studio/pull/5) | #4 branch (+ merges #1) |
| 4 | TASK-0004 | Review and harden core MVP compiler, runtime and run API | done (in `develop`) | [#7](https://github.com/quinguyen1502/langgraph-studio/pull/7) (plan: [#3](https://github.com/quinguyen1502/langgraph-studio/pull/3)) | #6 branch |
| 5 | TASK-0005 | Real LLM providers with per-workflow credentials | done (in `develop`) | [#9](https://github.com/quinguyen1502/langgraph-studio/pull/9) (replaces [#2](https://github.com/quinguyen1502/langgraph-studio/pull/2)) | #8 branch |
| 6 | TASK-0016 | Run trace timeline UI | done (in `develop`) | [#6](https://github.com/quinguyen1502/langgraph-studio/pull/6) | #5 branch |
| 7 | TASK-0017 | Restructure backend into layers (SQLAlchemy + Alembic) | done (in `develop`) | [#8](https://github.com/quinguyen1502/langgraph-studio/pull/8) | #7 branch |
| 8 | TASK-0018 | API envelope, English error codes, frontend i18n (en/vi) | done (in `develop`) | [#10](https://github.com/quinguyen1502/langgraph-studio/pull/10) | #9 branch |
| — | (re-plan) | Phases + task renumbering (DEC-0007) | — | [#4](https://github.com/quinguyen1502/langgraph-studio/pull/4) | `main` |

**Merge order:** #4 → #1 → #3 → #5 → #6 → #7 → #8 (TASK-0017) → #9 (TASK-0005) → #10 (TASK-0018). PR #2 is superseded by #9 (same feature on the layered backend) and can be closed without merging. After each merge, retarget the next stacked PR to `main`. PR #3 (TASK-0004 plan only) is superseded by #7 and can be closed once #7 merges, or merged first; its files are identical on #7.

## Phase 2 — Usable

Phase 2, Phase 3, and Phase 4 are done and merged into `develop`.

- TASK-0006 Human-in-the-loop (REQ-0003): **done** — merged into `develop` 2026-10-17
- TASK-0007 API / webhook trigger (REQ-0004): **done** — merged into `develop` 2026-10-17
- TASK-0008 Workflow versioning (REQ-0005): **done** — merged into `develop` 2026-10-17
- TASK-0009 Postgres + Redis + Docker Compose (REQ-0008): **done** — merged into `develop` 2026-10-17
- TASK-0010 Observability (REQ-0010): **done** — merged into `develop` 2026-10-17
- TASK-0019 Phase-2 hardening (open issues of TASK-0006/7/8/9/10): **done** — merged into `develop` 2026-10-17
- TASK-0020 Deferred hardening (notifications, webhook delivery log/retry/rotation, checkpoint recovery, lease reaper, live spans + OTel metrics): **done** — merged into `develop` 2026-10-17
- TASK-0021 Effectively-once side effects (idempotency keys, node ledger, fencing), fan-out/imported checkpoints, lost-span export, live notifications + preferences: **done** — merged into `develop` 2026-10-17
- TASK-0022 Human-in-the-loop approval through external channels (Slack, Telegram; adapter interface for WhatsApp/Teams/e-mail later): **done** — merged into `develop` 2026-10-17. Follow-up commits on the same PR: verified identities (one-time code by bot DM), org-wide admin channels, en/vi chat texts, API `callback_url` after a channel resume, several Slack workspaces per owner (team_id routing), callback rate limits; then per-workspace identities, a DB-enforced single verified owner, one idempotent callback path for every resume source, `STUDIO_TRUSTED_PROXIES`, and a Settings page (`/settings/channels|accounts|audit`) replacing the dialog

## Phase 3 — Advanced

- TASK-0011 Subgraphs and parallel branches (REQ-0006): **done** — merged into `develop` 2026-10-17 (PR #21)
- TASK-0012 RAG node (REQ-0007): **done** — merged into `develop` 2026-10-17 (PR #22)
- TASK-0013 MCP tools (REQ-0011): **done** — merged into `develop` 2026-10-17 (PR #23)
- TASK-0014 RBAC and sharing (REQ-0012): **done** — merged into `develop` 2026-10-17 (PR #24)
- TASK-0029 Phase 3 hardening (teams, ownership transfer, audit log, user deletion, org-resource policy, subgraph leftovers; DEC-0024): **done** — merged into `develop` 2026-10-17 (PR #25). Slack Enterprise Grid stays out of scope.

## Phase 4 — Last

- TASK-0015 Repo import hardening + container sandbox (REQ-0009). **done** — merged into `develop` 2026-10-18 (PR #33). The import feature stays **experimental**; `STUDIO_ENABLE_IMPORT` defaults off. Docker sandbox when the flag is on. REQ-0009 is Implemented (owner accepted Docker on 2026-10-18).

## Phase 5 — Editor UX

Added on 2026-10-17 at the owner's request. Status: done (PRs #26–#31 merged into develop on 2026-10-17).

- TASK-0023 Editor hotkeys and shortcut cheatsheet (REQ-0013) — done, DEC-0026
- TASK-0024 Editor undo and redo history (REQ-0014), after TASK-0023 — done, DEC-0027
- TASK-0025 Workflow template library: starter templates, save as template, import/export (REQ-0015) — done, DEC-0028
- TASK-0026 Copy, paste and duplicate nodes (REQ-0016) — done, DEC-0029
- TASK-0027 Auto-layout for the workflow canvas (REQ-0017) — done, DEC-0030
- TASK-0028 Command palette (REQ-0018) — done, DEC-0031


## LLM providers

- TASK-0030 Local and routed LLM providers: Ollama, LM Studio, generic OpenAI-compatible (vLLM / llama.cpp / LocalAI), OpenRouter; provider registry, model list, test connection (DEC-0032, Accepted 2026-10-18): **done** — PR #32 merged into `develop` (migrations 0024_credential_headers, 0025_kb_dims).

## Node execution settings

- TASK-0031 Per-node retry, timeout, and cache (REQ-0019, Implemented 2026-10-18): **done** — PR [#34](https://github.com/quinguyen1502/langgraph-studio/pull/34). REV-0030, QA-0030.

## Editor polish

- TASK-0032 Editor polish and bilingual README (REQ-0020, Implemented 2026-10-18): **done** — PR [#35](https://github.com/quinguyen1502/langgraph-studio/pull/35). REV-0031, QA-0031.

## Delivery records

- TASK-0033 Align requirement status and the integration branch (REQ-0021, Implemented 2026-10-18): **done** — PR [#36](https://github.com/quinguyen1502/langgraph-studio/pull/36). DEC-0033 supersedes DEC-0002. REV-0032, QA-0032.
- TASK-0034 JSON fold tooltip and `spliceNode` tests (REQ-0022, Implemented 2026-10-18): **done** — PR [#37](https://github.com/quinguyen1502/langgraph-studio/pull/37). REV-0033, QA-0033.

## Node input

- TASK-0035 Per-node input fields (REQ-0023, Implemented 2026-10-18): **done** — PR [#38](https://github.com/quinguyen1502/langgraph-studio/pull/38). REV-0034, QA-0034.

## Run one step

- TASK-0036 Run one superstep, or until a chosen node, then pause (REQ-0024, Approved 2026-10-18): **done** — PR [#39](https://github.com/quinguyen1502/langgraph-studio/pull/39) merged into `develop` 2026-10-18. REV-0035, QA-0035. Independent of TASK-0037.

## Canvas note

- TASK-0037 Sticky note on the flowchart (REQ-0025, Approved 2026-10-18): **done** — PR [#40](https://github.com/quinguyen1502/langgraph-studio/pull/40) merged into `develop` 2026-10-18. REV-0036, QA-0036. Independent of TASK-0036.

## Editor panels

- TASK-0038 Drag to resize the palette, the config panel, and the run panel (REQ-0026, Implemented 2026-10-18): **done** — PR [#41](https://github.com/quinguyen1502/langgraph-studio/pull/41) merged into `develop` 2026-10-18. REV-0037, QA-0037.

## Review hardening

- TASK-0039 Fixes from the 2026-10-18 project review: HTTP Tool SSRF guard, Condition matching, macOS Playwright, editor header at 1280px, records, CORS, log redaction, lazy routes (REQ-0027, Implemented 2026-10-18): **done** — PR [#42](https://github.com/quinguyen1502/langgraph-studio/pull/42) merged into `develop` 2026-10-18. REV-0038, QA-0038.

## Editor maintenance

- TASK-0040 Split `Editor.tsx` into `components/editor/` and clear the React hook oxlint warnings (REQ-0028, Implemented 2026-10-18): **done**. REV-0039, QA-0039. Merged (PR #43).
- TASK-0041 Template editor with state field chips for node message fields (REQ-0029, Implemented 2026-10-18), with the editor header overlap and `sm` button icon offset: **done**. REV-0040, QA-0040. Merged (PR #44).
- TASK-0042 Commit `.claude/launch.json` (backend and frontend dev servers for the Claude app preview): **done**. Merged (PR #45).
- TASK-0043 Template insert menu focus and vendor chunks (REQ-0030, Implemented 2026-10-18): **done**. REV-0041, QA-0041. Merged (PR #47).
- TASK-0044 Template paths and filters (REQ-0031, DEC-0034, Implemented 2026-10-18): **done**. REV-0042, QA-0042. Merged (PR #48).

## Sign-in hardening

- TASK-0045 Sign-in lockout, password reset links, HttpOnly session cookie, no demo account in production (REQ-0032, DEC-0035, Implemented 2026-10-18): **done**. REV-0043, QA-0043. Merged (PR #49).

## Scheduled runs

- TASK-0046 Cron schedules for workflow runs (REQ-0033, DEC-0036, Implemented 2026-10-19): **done**. REV-0044, QA-0044. Merged (PR #50).

## More approval channels

- TASK-0047 WhatsApp buttons, e-mail and Teams links to /approve (REQ-0034, DEC-0037, Implemented 2026-10-19): **done**. REV-0045, QA-0045. Merged (PR #51).

## Records

- TASK-0048 Close the open questions of REQ-0001, 0002, 0003, 0004, 0008 and 0010; accept DEC-0006; DEC-0033 addendum on release merges to main: **done**. Merged (PR #52).

## Loops

- TASK-0049 For each node: run a branch once per list item, one at a time (REQ-0035, DEC-0038, Implemented 2026-10-19): **done**. REV-0046, QA-0046. Merged (PR #54).

## Decision models

- TASK-0050 Decision (Jev) node: typed questions to TypeSafe System One, answers to state (REQ-0036, DEC-0039, Implemented 2026-10-19): **done**. REV-0047, QA-0047. Merged (PR #55).

## E-mail

- TASK-0051 SMTP credentials and Send email node: dry run without a credential, effectively-once sending, hourly recipient quota (REQ-0037, DEC-0040, Implemented 2026-10-19): **done**. REV-0048, QA-0048. Merged (PR #56).

## Accounts

- TASK-0052 Profile page and self-service password change (REQ-0038): **merged** (PR #58, REV-0049, QA-0049).

## Code nodes

REQ-0039, Accepted and Implemented 2026-10-19; CLAR-0001 answered; DEC-0041 Accepted 2026-10-19; tasks approved by the owner.

- TASK-0053 Code mode runtime: Docker sandbox with no network, `studio-code` image, node mode and validation. **merged** (PR #61, REV-0050, QA-0050). Independent of TASK-0054.
- TASK-0054 `code.write` permission, checked on every path that writes a graph. **merged** (PR #62, REV-0051, QA-0051). Independent of TASK-0053.
- TASK-0055 Editor: Python code field, Test with sample state, trace output. **merged** (PR #63, REV-0052, QA-0052). After TASK-0053 and TASK-0054.
- TASK-0056 Host subprocess runtime and the eight "not isolated" warnings. **merged** (PR #64, REV-0053, QA-0053). After TASK-0053 and TASK-0055.

## Documentation

- Handbook on Zensical (English and Vietnamese sites from one page tree), a platform-style README, and a 70 s quickstart video recorded from the UI by `frontend/e2e/quickstart.spec.ts` (`handbook/`, `scripts/promo/`): **merged** (PR #65).

## Rename

- TASK-0058 Rename the product to **Superstep** (UI, backend strings, Compose, handbook, video, README), keeping v0.1.0 installs working: **merged** (PR #69, plan PR #68, REV-0054, QA-0054); released to `main` in PR #70. The owner renamed the repository on 2026-10-20 and chose not to redirect the old docs URL, so the redirect files were removed.
- TASK-0059 Never drop the history write of a cancelled run (flaky Postgres CI: `test_disconnect_cancels_run`, `test_timeout`, approval callback): **merged** (PR #73, REV-0055, QA-0055). The Postgres CI job passed 4 consecutive runs before the merge.
- TASK-0060 Clear the run bus entry of a run cancelled while the loop shuts down (REV-0055 follow-up): **merged** (PR #76, REV-0056, QA-0056).
- TASK-0061 Center the search icon and clear button in search boxes (owner report): **merged** (PR #77).
- TASK-0062 Docs tell readers to sign up instead of using the demo account (owner request): **merged** (PR #80).

## Channel templates and logos

REQ-0040, Accepted 2026-10-20 (the owner chose brand colours and 8 templates), Implemented 2026-10-21.

- TASK-0063 Channel logos in brand colours (Channels, My accounts, Human node select, Audit log, connection items), DEC-0042: **merged** (PR #83, REV-0057, QA-0057).
- TASK-0064 Eight built-in templates for real processes (refund, leave, social post, large order, expense claim, purchase request, support escalation, feedback digest), built-in names in en and vi: **merged** (PR #84, REV-0058, QA-0058).
- TASK-0073 Translate the "not connected" label on a Human node whose channel has no connection yet (owner report: the select showed `approvals.notConnected`): **merged** (PR #95, REV-0066, QA-0066).

## Approval deadlines and inbox

REQ-0041, Accepted 2026-10-21 (the owner chose deadlines with reminders and one inbox for approvals), Implemented 2026-10-21.

- TASK-0065 Approvals inbox: one list of the runs waiting on the user, as owner or listed approver, answered in place; approvers on studio-only nodes; DEC-0043: **merged** (PR #86, REV-0059, QA-0059).
- TASK-0066 Human node deadlines: reminders, then reject, approve or escalate once; due times in the inbox; deadlines on the six channel templates: **merged** (PR #87, REV-0060, QA-0060).

## Workflow tests

REQ-0042, Accepted 2026-10-21 (the owner chose real models by default with a mock option, CI runs later, and test cases only on built-in templates), Implemented 2026-10-22.

- TASK-0067 Test cases (input, Human answers, checks), Run all / run one on the current version, test runs that send no e-mail, channel message, notification or callback, mock model option, Tests panel, DEC-0044: **merged** (PR #89, REV-0061, QA-0061).
- TASK-0068 Comparison with the latest suite run on an earlier version (Regression, Fixed, New), Run against version, suite history, Save as test case from a run, stale checks: **merged** (PR #90, REV-0062, QA-0062).
- TASK-0069 Test cases on every built-in template, copied to workflows made from them; handbook "Workflow tests" page (en, vi): **merged** (PR #91, REV-0063, QA-0063).

## Export to Python

REQ-0043, Accepted 2026-10-22 (the owner chose a runnable file with the mock by default, English comments, and subgraphs as their own graphs), Implemented 2026-10-22.

- TASK-0070 Generator: one readable, runnable LangGraph `.py` per workflow version, API route, same-path check against the studio's mock run for every built-in template, DEC-0045. **merged** (PR #93, REV-0064, QA-0064).
- TASK-0071 Editor "Code" tab ("View as code"; other languages may follow): code beside the canvas, the selected node's function highlighted, Copy and Download. **merged** (PR #94, REV-0065, QA-0065).
- TASK-0072 Handbook "Export to Python" page (en, vi) with the canvas → code table and a screenshot. **merged** (PR #96, REV-0067, QA-0067).

## Chat triggers

REQ-0044, Accepted 2026-10-22 (CLAR-0002: only verified linked chat accounts with the run right, a command word, one reply field, one input field), Implemented 2026-10-22.

- TASK-0074 Chat trigger rows per workflow, management API (share right, unique command per connection and place), Slack scopes check, Telegram webhook for messages, DEC-0046. **merged** (PR #98, REV-0068, QA-0068).
- TASK-0075 Slack events and Telegram messages start `source="chat"` runs; thread replies (started, result, error, waiting), private refusals, dedupe, rate limit, audit. **merged** (PR #99, REV-0069, QA-0069).
- TASK-0076 Editor "Chat triggers" dialog, Channels page events URL and missing-scope warning, Chat badge and sender in run history. **merged** (PR #100, REV-0070, QA-0070).
- TASK-0077 Handbook "Chat triggers" page (en, vi) with Slack and Telegram setup and a screenshot. **merged** (PR #101, REV-0071, QA-0071).
- TASK-0083 Settling a run (chat reply, callback, test record) survives a cancelled handler: `settled()` uses `_write_in_thread`; fixes the flaky `test_waiting_then_finished_and_errors`. **merged** (PR #113, REV-0076, QA-0076).
- TASK-0086 Alignment guardrails: ui-conventions rule 11 (one size variant per row, no hand-set heights/paddings/leading, baseline alignment), `e2e/helpers/alignment.ts` + `alignment.spec.ts`, `npm run lint:ui` on CI; editor and list headers fixed. **draft PR** (REQ-0049, DEC-0055, REV-0079, QA-0079).

## Vietnamese language quality

REQ-0045, Approved 2026-10-23 (owner approved the glossary and fix plan steps 1-8; archive tags and branch pruning skipped), Implemented 2026-10-23.

- TASK-0078 Glossary (ui-conventions rule 10), vi locale polish and natural-Vietnamese pass, locale parity/glossary test, README features, Vietnamese handbook wording. **merged** (PR #107).

## TypeScript in Code mode

REQ-0046, Accepted 2026-10-23 (feasibility study Option A: Deno; owner approved P0-P2, P3 out of scope), Implemented 2026-10-23.

- TASK-0079 Code-mode language registry (`engine/code_languages.py`), `data.language` (default Python), `STUDIO_CODE_LANGUAGES`, `CODE_LANGUAGE_UNSUPPORTED`, DEC-0048. **merged** (PR #109, REV-0072, QA-0072).
- TASK-0080 TypeScript on Deno: `code_runner.ts`, zero-permission `deno run`, V8 heap cap, npm allowlist (`STUDIO_CODE_TS_PACKAGES`), `docker/studio-code-ts`, compose and CI (Deno for pytest, a Docker job that builds both Code images), DEC-0049. **merged** (PR #110, REV-0073, QA-0073).
- TASK-0081 Editor: `CodeEditor` (CodeMirror Python/TypeScript) with a language picker, TypeScript starter, generated `State` type and `state.` completions, "TS" canvas badge, per-language admin card, en/vi, glossary, handbook (en, vi), vitest and e2e `code-typescript.spec.ts`, DEC-0050. **merged** (PR #111, REV-0074, QA-0074).

REQ-0047, Accepted 2026-10-23, Implemented 2026-10-23: the LangGraph.js export, deferred as P3 of REQ-0046, is now in scope (the other P3
items, type-check diagnostics and full IntelliSense, stay out).

- TASK-0082 TypeScript export: `export_common.GraphWriter` shared by both exporters, `typescript_export.to_typescript`, the `exporters` registry, `?language=` on the export API (`EXPORT_LANGUAGE_UNSUPPORTED`, `TYPESCRIPT_EXPORT_UNAVAILABLE`), Code tab language picker, en/vi, handbook (en, vi), snapshot + `deno check` tests, DEC-0051. **merged** (PR #112, REV-0075, QA-0075).

## Agent chat

REQ-0048, Accepted 2026-10-23 (owner decisions 1-6 on audience, access, memory, Human "answered by", step visibility,
attachments/embed later and retention; DEC-0052, DEC-0053, DEC-0054). Phase 1: the studio Chat tab.

- TASK-0084 Web chat backend: chat sessions and turns (migration 0035), the `web` chat trigger with its settings, one
  `source="chat"` run per message over the run socket with the history window, reply-once answers, `node_token.field`,
  Human `answered_by`, retention cleanup, `CHAT_*` errors. merged in #116 (REV-0077, QA-0077).
- TASK-0085 Studio Chat tab: shadcn Message Scroller / Message / Bubble / Trace / Code Block, a sanitised Markdown answer,
  chats list and New chat, Builder / Visitor view by the step setting, Human nodes answered in the chat or waiting for
  a reviewer, the Chat settings dialog, the Human "Answered by" option, handbook pages. merged in #117 (REV-0078, QA-0078).

## Comparison pages

REQ-0069, Done.

- TASK-0113 Handbook: Superstep vs visual builders and vs agent frameworks (en, vi). **merged** (PR #141, REV-0105, QA-0105).

## Workflows as MCP tools

REQ-0070, Done. DEC-0061.

- TASK-0114 Opted-in workflows as MCP tools at `/mcp` (Streamable HTTP), migration 0038. **merged** (PR #142, REV-0106, QA-0106).

## Runs across restarts

REQ-0071, Done. DEC-0062.

- TASK-0115 Start-up recovery for the in-memory queue, and restart tests. **merged** (PR #143, REV-0107, QA-0107).
- TASK-0127 An answer to a waiting run is kept on the run until the resumed segment records something, so a restart
  does not lose it (migration 0039). **merged** (PR #163, REV-0115, QA-0115).

## Agent node

REQ-0072, Accepted 2026-10-25, Done 2026-10-26 (CLAR-0003: all recommended options; inline tools, approval as for Human nodes,
approve or reject, a rejection is told to the model, a last call without tools at the round limit, answer plus
optional steps, optional history field, Python and LangGraph project exports first). DEC-0063 (accepted 2026-10-25): the node is
expanded into LangGraph model and tool steps, one tool call per step.

- TASK-0116 Engine: expansion, model calls with tools through the provider registry (Anthropic over plain HTTP),
  MCP / HTTP / built-in / knowledge base tools, round limit, mock, validator, errors. **merged** (PR #144, REV-0108, QA-0108).
- TASK-0117 Approval before a tool call through the Human approval path; restart tests. **merged** (PR #146, REV-0110, QA-0110).
- TASK-0118 Editor settings, trace grouping by round, chat steps, e2e. **merged** (PR #145, REV-0109, QA-0109).
- TASK-0119 "Tool called" test check, Support agent template with tests, Python and project export, TypeScript
  refusal. **merged** (PR #147, REV-0111, QA-0111).
- TASK-0120 Handbook (en, vi), comparison pages, CHANGELOG. **merged** (PR #148, REV-0112, QA-0112).
- TASK-0125 LangGraph.js export of Agent nodes (CLAR-0003 question 8, also REQ-0047); the TypeScript refusal is
  removed. **merged** (PR #158, REV-0113, QA-0113).

## Owner requests

Asked for in chat, with no requirement of their own. Review and QA are in each task file unless an artifact is named.

- TASK-0121 Phone layout, and one fixed set of Config tabs for every node. **merged** (PR #150).
- TASK-0122 Intro video remade with the new features (en, vi). **merged** (PR #152).
- TASK-0123 Fixes: time travel after a Condition (REQ-0051), and restart recovery counting resumes (REQ-0071).
  **merged** (PR #153).
- TASK-0126 Vietnamese "Hàm" label, a "choose a knowledge base" hint, and the template's missing setup listed when
  it opens (REQ-0007, REQ-0015, REQ-0072). **merged** (PR #160, REV-0114, QA-0114).
- TASK-0129 Factory housekeeping: review and QA records for TASK-0125 to TASK-0128, requirement statuses, this
  roadmap, DEC-0064, verification commands in the tool policy. **merged** (PR #168).
- TASK-0130 Per-command `factory verify` timeout (framework 6e66d20); the backend suite gets 900 s. **merged** (PR #170).
- TASK-0131 Framework fixes (513545e): skills update unedited copies, `gc --no-tasks` / `--no-runs`, `deps` skips build
  output and records portable commands. **merged** (PR #172).
- TASK-0132 Workflow check messages in the UI language: codes in the API (`issues`), `validation.<CODE>` in
  both locales, DEC-0065 (REQ-0045). **review** (REV-0116, QA-0116).

## Releases

- TASK-0124 Version 0.7.0: comparison pages, workflows as MCP tools, runs across restarts, Agent node, phone layout,
  intro video. **released** (PR #155 to main, tag `v0.7.0`).
- TASK-0128 Version 0.8.0: the TypeScript export of Agent nodes, template setup hints, an answer kept across a
  restart. **released** (PR #166 to main, tag `v0.8.0`).
- Earlier releases (0.3.0 to 0.6.0: TASK-0096, TASK-0098, TASK-0100, TASK-0105, TASK-0111) and the tasks between
  TASK-0087 and TASK-0112 are not listed in this roadmap. Their task files and CHANGELOG.md have the details.
