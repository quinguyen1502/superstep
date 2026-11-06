# Browser tools in the existing editor

TASK-0250 / REQ-0086. Configure infrastructure in Settings → MCP servers first
([connection settings](browser-settings.md)). Browser tools stay ordinary MCP
tools on an existing Agent or MCP node. There is no Browser canvas node or second
Agent/model setting. The usual General, Settings, Data and Execution tabs remain.

## Agent and dynamic URLs

In Agent Settings, add one MCP tool row per permitted operation and select the
saved connection/tool. Click/fill always need a verified human reviewer; this
switch cannot be disabled. Reviewer channels/deadlines use the existing controls.
Automatic approval is not offered for a browser-only tool set and cannot grant
browser authority in the backend. Mixed tool sets retain automatic approval for
their ordinary tools only.

For browser navigate or web fetch, Data exposes the URL source:

- Agent-filled: use the URL from chat or an explicitly configured search tool.
  Ask for the site/organisation when context is missing. No hidden start URL.
- Fixed: one literal HTTP(S) URL, without rendering model arguments into it.
- State: one existing state reference, with supported filters, rendered once.

Source toggling preserves the current field drafts; only the chosen source is
saved. Fixed/state bindings are removed from the model's URL parameter and cannot
be overridden by a call. Search remains its own explicitly granted web tool,
without a browser login or proxy. Existing prompts/Human questions handle missing
business context; choosing a URL source does not invent an organisation or search
provider. Execution shows connection action/idle/lifetime limits. Browser calls
in one Agent/connection session stay ordered even when ordinary tools overlap.
Lost/expired/unknown effects do not gain a retry through node retry/cache settings.

## Reusable recipe

A recipe is an ordinary saved workflow with a typed root contract. Select Start:
Settings enables the recipe and chooses one browser connection; changing it
updates the draft MCP actions. Data selects required primitive inputs and declared
object results. Build one Start → 1–20 MCP actions → one End, with a single linear
path. Agent/loop/branch/retry/cache definitions are rejected on Save.

On each MCP action, Settings selects the operation and Data configures arguments,
output and targets. Recipe click/fill chooses an earlier navigate/snapshot output,
literal role and exact text; fill values use the existing TemplateEditor. Extract
chooses output keys, one earlier observation and role/optional exact text. Role-only
extraction must be unique. Missing/ambiguous/stale targets stop. Snapshot again
after an effect. The UI's selectors do not replace worker fingerprints, page
generation, current policy or exact-target human receipts.

Choose the saved recipe through an Agent's existing Another workflow tool. Its
declared inputs/results are selected automatically and cannot be changed there;
the model fills the closed typed input schema. A recipe never switches to an
autonomous fallback. Save/reload preserves browser_recipe metadata. Explicit
recipe-contract, extraction-target and Agent-tool removal uses the shared exact-name
confirmation. Disabling the recipe leaves ordinary MCP actions that need ordinary
runtime arguments; it does not silently convert literal selectors into raw refs.

## Trace and public chat

The existing ordered timeline shows browser status. Output detail displays bounded
escaped observation text, safe origin, page generation and result preview. It
explains missing URL, approval, challenge, expiry, lost page, stale target, policy
denial and unknown effects, with no automatic resend action. Preview text/element
and extracted-value bounds are presentation limits, separate from execution data.

Private captures load only after an explicit click through the shared API client.
The existing owner-only artifact endpoint rechecks access/expiry. A denied/expired
capture shows a translated error; there is no public/signed image link. Blob URLs
are revoked on unmount. Captures may contain private page text even when fields
are masked.

Runtime events mark browser-containing workflows (including recipe children) as
private. Public sockets and persisted visitor views strip all intermediate
input/delta/model/tool/code/error payloads from those runs, including later state
echoes. Only allowlisted operation/status/approval facts and ordinary step labels/
timing survive. Legacy browser envelopes/Agent metadata also mark stored histories
for filtering. Browser review prompts are not persisted as chat turn text, so
deleting run history cannot uncover a private target. Review authority remains in
the authenticated inbox/channel, never in public chat. The Studio run inspector
and builder's own chat view retain authorised details. Raw worker envelopes used
as a final chat reply are reduced to safe facts, including JSON string envelopes.

The workflow's intentionally selected final answer/declared recipe result remains
its output contract. This is not an assurance that arbitrary model-authored prose
cannot repeat business data it has been given; builders must choose the appropriate
final answer and data scope. No raw intermediate state is published merely by
selecting full chat steps.

The feature remains experimental/default off. This task adds no schema/dependency,
provider deployment or export runtime. Python/TypeScript executable exports and
the consolidated handbook/acceptance remain TASK-0251/0252/0253.
