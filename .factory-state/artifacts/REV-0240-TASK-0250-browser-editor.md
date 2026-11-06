# Review

## Metadata

- Project: superstep
- Review ID: REV-0240
- Task ID: TASK-0250
- Reviewer: Codex (self-review; owner review pending)
- Created: 2026-11-06
- Updated: 2026-11-06
- Outcome: scoped conditional pass; full declared verification running

## Scope And References

Source 8dc9291d relative to task-start 79abf13e. REQ-0086, DES-0004,
ARCH-0002/DEC-0085, PLAN-0006, docs/ui-conventions.md and docs/browser-editor.md.
Explicit unmerged stack on TASK-0249 47a9b2bc / #314 (latest 17da46fc records
all eight checks passed), #313/#312/#311 and earlier prerequisites. Parent final
metadata/locale follow-ups are not incorporated; no merge performed.

## Findings

No blocking scoped source finding. Agent/MCP tools retain existing nodes and
General/Settings/Data/Execution tabs. Data owns model/fixed/state URL bindings;
the backend strips bound URLs from the model schema and renders state once.
Provider/proxy/profile authority remains on saved connections. Click/fill approval
is mandatory; reviewer settings are visible without an optional approval flag,
and browser-only tool sets do not offer automatic approval. Browser limits are
displayed as inherited policy rather than silently expanded by UI values.

Recipes remain ordinary saved workflows. Start hosts the root contract; MCP Data
hosts literal semantic targets and runtime input templates. Editor save/load now
preserves browser_recipe, and selecting a recipe as Another workflow adopts its
closed input/result contract. Missing/ambiguous/stale targets still fail under the
existing worker/recipe rules. Exact-name removal covers recipe contract, extraction
targets and Agent tools. Lookup errors are visible and do not select an unusable
workflow; stale asynchronous metadata responses are ignored.

Privacy refinement: runtime marks browser-containing workflows, including child
recipes. Public live/history filtering uses an allowlist of operation/status/
approval facts and removes intermediate state, Agent/tool/model payloads, code and
errors across the whole run. Legacy envelopes and later state echoes are covered.
Browser review prompts are not persisted in chat turn text; raw worker envelopes
used as final replies reduce to facts. Owner run detail retains bounded escaped
observations and explicitly loaded protected captures. The API helper's binary
mode shares existing authentication/error translation; image reads remain owner/
expiry checked. No public URL or bytes enter chat.

## Standards And Design Alignment

No schema/dependency/new browser runtime/model loop or canvas taxonomy. Engine
computes presentation facts, services enforce visitor filtering, existing API
auth/artifact service remains unchanged. Shared React owns chat status rendering;
locales/theme tokens/shared controls and exact-name confirmation are reused.
All new text has en/vi keys. Colour/hex scans and strict UI class lint find no new
violation. Connection URLs remain literal Settings values; node state templates
use TemplateEditor, selectors use literal inputs and existing state pickers.
Wide/narrow light/dark screenshots were inspected outside Git.

## Validation Review

- Related backend: 76 passed, 1 optional PostgreSQL skip (24.55 s); final waiting
  metadata/approval/layers: 27 passed (13.19 s).
- Root npm test: frontend 167, shared React 22, TypeScript SDK 102 passed.
- Build/lint passed. New replay/chat, API blob and shared status tests passed.
- Chrome initial matrix: 8 passed (59.1 s). Expanded mobile/recipe invocation/
  search/fetch/trace regression: 11 passed (1.4 min). Existing Agent node regressions
  both passed in an earlier harness run. Final lookup/error and recipe recheck:
  2 passed (26.9 s), with no source edits after source commit 8dc9291d.
- Some initial test harness runs stopped on an incorrect CodeMirror selector or
  omitted mobile tab selection; corrected tests passed. No product relaxation.
- Full eight-command Factory profile running on clean source 8dc9291d.

## Risks, Follow-Up And Decision

Final answer/declared result is the workflow's publication contract; arbitrary
model prose cannot be proven free of business data it was intentionally given.
The change removes raw intermediate publication, not every semantic exfiltration
possibility. Captures can contain private rendered text and stay owner protected.
Trace UI states use controlled presentation fixtures; actual browser/effect/egress
proofs belong to prerequisites and final integrated acceptance. No live provider
or account setup. Runtime stays experimental/default off; exports remain
TASK-0251/0252 and integrated handbook/acceptance TASK-0253.

Conditionally approved for scoped QA pending full declared verification and owner
approval. No done/Ready/merge authority. Parent sync remains a separate pending
permission after automatic approval review rejected git merge; it does not block
current source verification or this Draft PR.
