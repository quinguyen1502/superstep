# Review

## Metadata

- Project: superstep
- Review ID: REV-0237
- Task ID: TASK-0247
- Reviewer: Codex (self-review; owner review pending)
- Created: 2026-11-06
- Updated: 2026-11-06
- Outcome: scoped pass; full declared verification passed

## Review Scope And Reference Artifacts

TASK-0247 source 01b3727e after task-start fdb92392, explicitly stacked on TASK-0246 #311 and #310/#309/#308/#304/#303/#299. Parent evidence update 8a16d5d7 is documentation only. REQ-0086, DES-0004, ARCH-0002 URL/web refinement, DEC-0085, PLAN-0006 and `docs/browser-web-tools.md`. No merge or release authority.

## Findings

No blocking finding in scoped implementation after focused validation. Binding metadata is builder-owned: fixed/state URLs are omitted from model parameters, resolved once before ticket reservation and cannot be overridden. Model values never undergo another template pass. Empty runtime URL returns missing_input with no worker/fallback. Existing MCP node templates remain the one expression language.

Separate web settings strictly reject browser/profile/proxy/authority arguments. Enabled tools are checked at discovery and execution through existing owner/org MCP authorization. Search headers stay encrypted/masked and are sent only to the fixed search endpoint. Fresh clients prevent cookie/environment/browser proxy inheritance. DestinationPolicy rejects all non-global/mixed/translation addresses, then the standard Host/SNI helper pins the connection. Redirects, compressed/oversize responses and provider failures have bounded explicit outcomes. Credential redaction precedes text clipping.

Resolved during development: malformed JSON search arrays could otherwise escape the declared failure contract; response shape now checks before reading fields. Shared missing-URL handling covers whitespace and standalone MCP nodes, not only Agent binding.

## Standards And Design Alignment

No new DB schema, dependency, endpoint or Agent loop. Pure engine contracts/templating and service-managed transport preserve layering and shared envelopes/errors. Existing browser approval/fencing still own effect authority. New UI controls, adapter labels/configuration UX and filtered public trace are intentionally TASK-0249/0250; this task supplies experimental backend metadata, not a UI acceptance claim. Existing typed-delete behavior is unchanged.

## Validation Review

Final URL/web/Agent/browser approval/layers suite: 84 passed. MCP/managed/parallel/approval/workflow-tool/public-chat/envelope regressions: 121 passed. Contract generation/whitespace passed. Full eight-command Factory profile is running on committed source 01b3727e. Search/fetch providers are controlled fakes; no live SearXNG/search-quality claim.

## Assumptions, Limits And Follow-Up

A syntactically valid public model URL is not proof of the correct business organisation. The Agent asks for ambiguous/missing identity; use fixed/state bindings and saved origins for a strict target. Search normalisation does not resolve every candidate domain; actual use enforces DNS policy. HTTP/body bounds do not promise an absolute OS DNS timeout. No custom web proxy, redirect following, JavaScript/PDF extraction or credential inheritance. UI and executable exports remain assigned tasks; feature defaults off.

## Review Decision

Conditionally approved for scoped QA, with full declared verification passed; owner review pending. No done/Ready/merge approval.

- Final canonical verification on committed 01b3727e (only documentation/evidence followed): all eight commands passed. Root build/lint/test 12.68/1.20/17.97 s; backend 478.82 s; Python SDK 13.73 s; TypeScript SDK build/test/typecheck 1.59/1.36/1.45 s. No backend/Node source changed during the run. Factory verify validation/IDs follow before publication; no owner merge approval.
