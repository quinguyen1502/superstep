# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0240
- Task ID: TASK-0250
- QA Owner: Codex (advisory; owner approval pending)
- Created: 2026-11-06
- Updated: 2026-11-06
- Outcome: scoped conditional pass; full declared verification running

## Scope And References

Source 8dc9291d; TASK-0250, REQ-0086, DES-0004, ARCH-0002/DEC-0085,
PLAN-0006, REV-0240, docs/browser-editor.md and docs/ui-conventions.md.

## Acceptance Criteria Coverage

- Existing taxonomy/tabs/model: passed source and Chrome inspection. Agent/MCP
  Settings grants tools, Data binds URLs/recipe arguments, Execution shows limits;
  Start Settings/Data edits the root recipe contract. No new canvas node/tab/model.
- Chat/state/search/context/recipe: passed model default without hidden URL,
  fixed/state draft switching, TemplateEditor tag/save/reload, separate search/
  fetch grants with fetch state binding, typed recipe root/targets save/reload and
  selection as Another workflow with locked declared inputs/results. Existing
  prompt/Human surfaces handle missing organisation/site context; runtime missing
  URL/search contracts were verified in TASK-0247. No browser-mode fallback.
- Privacy and stop states: passed actual RunService integration with scoped
  browser fixture, live/public/history/legacy filtering and later state echoes.
  Public facts omit refs, intent/command IDs, observations, capture IDs and raw
  input. Browser reviewer prompt is not persisted in chat text. Raw final worker
  envelopes/JSON strings reduce to safe facts. UI fixtures cover confirmed,
  waiting, challenge, expiry, session loss, unknown, missing URL, denial, stale
  observation and rejected/expired approval; unknown has no resend action.
  Capture stays unloaded until explicit click and shows a translated denied/
  expired result. Actual artifact owner/retention enforcement is unchanged and
  tested by prerequisite backend/runtime coverage.
- Keyboard/mobile/en/vi/themes/trace: passed four locale/theme combinations,
  390px no-horizontal-overflow, keyboard tab order, command-palette navigation,
  root/action/Agent Data screenshots and existing Agent/trace regressions. Shared
  React status renderer and timing/replay tests preserve generic behavior.

## Checks Performed

- Final related backend suite: 76 passed, 1 optional PostgreSQL skip (24.55 s).
- After waiting-event metadata: presentation/approval/layers 27 passed (13.19 s).
- Root npm test: 167 frontend + 22 React + 102 TypeScript SDK tests passed.
- Root build/lint passed; no new warnings in browser components; strict UI class
  guard and changed-component colour/hex scans have no hits.
- Chrome first full matrix: 8 passed (59.1 s); expanded matrix with mobile,
  recipe-tool invocation, separate web grants and trace regressions: 11 passed
  (1.4 min). Existing Agent node regressions: 2 passed in earlier harness run.
  After final lookup handling: 2 passed (26.9 s). Harness selector/tab mistakes
  were corrected without changing product behavior.
- Full Factory eight-command verification running on clean commit 8dc9291d.

## UX And Accessibility Evidence

Four conventional tabs, shadcn/theme tokens, shared exact-name dialogs, labelled
inputs and controlled selectors. Recipe observation only picks earlier outputs;
it does not offer creation of an unwritten observation. Missing schema fields
still use existing explicit creation actions where appropriate. Browser-only
automatic approval controls are absent; mandatory reviewer controls remain.
Lookup errors stay visible. Captures require explicit access-checked load.

Screenshots outside Git at /private/tmp/superstep-browser-ui-shots-20261106 cover
Agent Data/Execution, recipe root/action/narrow layout and trace detail in en/vi
light/dark. Visual inspection found no clipped fields, unreadable theme content
or page overflow. Images are not committed. Binary/API error and shared renderer
tests cover the same presentation seams without a Studio-only client in React.

## Gaps And Residual Risk

Full canonical profile pending. Browser fixture UI statuses are controlled
presentation data; this task does not claim a fresh real Docker run for every
theme. Actual worker/remote/proxy/effect proofs already exist in prerequisites;
final consolidated acceptance is TASK-0253. Arbitrary model-authored final prose
still depends on the workflow's intentional output/data contract. Captures can
contain private site text despite masked controls. Existing runtime feature gate
stays off. No live account/provider setup, export claim, release or merge.

## QA Decision

Conditionally passed for scoped review pending full profile and owner approval.
No done/Ready/merge authority. Parent follow-up sync remains separately pending
permission after automatic merge-review rejection; current committed source and
verification are independent of that sync.
