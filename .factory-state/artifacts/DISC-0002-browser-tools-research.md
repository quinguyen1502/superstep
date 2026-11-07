# Project Discovery

## Metadata

- Project: superstep
- Discovery ID: DISC-0002
- Status: Observed repository evidence and research synthesis; not implementation approval
- Owner: Thái Quí Nguyễn
- Created: 2026-11-03
- Updated: 2026-11-06

## Scope

Browser tools for existing Agent/MCP nodes, dynamic URLs, session lifecycle, recipe reuse, proxy placement and portable exports. Repository inspected in this detached worktree at `7c7348bce38f2fd619e011b547a09180858b00fc`; fetched `origin/develop` was `6218d84071d882001c4da96896759f0e48839ebe`. Reconfirm contracts against the integration branch at task-start. No source or task-start action performed.

## Context Sources

- `vision.md`, `project.md`, `roadmap.md`, `project-specs.md`: LangGraph workflow builder, mock/offline use, layered backend and established source-approval distinctions.
- `backend/app/engine/mcp_client.py`: short initialize/list-or-call/close session; stdio process terminates and HTTP session is deleted at close. A browser cannot assume continuity across these calls.
- `backend/app/services/mcp_service.py`, `services/managed_tool_service.py`, `engine/ports.py`: owner/org-bound discovery/call, encrypted connection secrets, operation keys and managed outcome ledger. Current ports need run/session context for browser behavior.
- `backend/app/engine/agents.py`, DEC-0069: tool calls can execute concurrently; a per-browser ordering rule must coexist with unrelated parallel tools.
- `backend/app/engine/python_export.py`, `typescript_export.py`, `project_export.py`, `McpService.check_export`: MCP placeholders and explicit managed export refusal. Browser export is new work, not inherited functionality.
- `backend/app/core/net.py`, `services/managed_tools/base.py`: DNS pinning protects outbound HTTP clients, not native browser traffic/CDP-generated subresources or upstream proxy resolution.
- `backend/app/engine/tools.py`, `services/managed_tools/__init__.py`: no first-class browser or normalised web-search/fetch tool implementation found in these registries. Search can initially reuse a configured MCP/HTTP provider.
- `frontend/src/components/mcp-settings.tsx`, `managed-connection-fields.tsx`, `agent-settings.tsx`, `docs/ui-conventions.md`: reuse current connection/tool forms; retain common node-config tabs.
- `.factory-state/previews/browser-tool/browser-workspace.html`: latest concept separates connections, Agent tools and recipes; explores chat/workflow/search/missing-context inputs. It remains a simulation and currently omits the later-discussed proxy form.
- Existing TASK-0224 worktree lifecycle change is unrelated and left untouched.

## External Research

Official documentation consulted during this conversation (2026-11-02/03); no vendor reliability, anti-bot or performance benchmark performed. Links are evidence of concepts, not an instruction to install their current SDK/API without rechecking versions.

| Source | Observation relevant to this requirement |
| --- | --- |
| https://n8n.io/integrations/airtop/ and https://docs.airtop.ai/guides/integrations/n8n | Browser actions and session/window lifecycle can be integrated with a workflow builder. |
| https://docs.n8n.io/build/integrate-ai/ai-examples/use-ai-for-parameters.md | Agent-filled tool parameters come from task/tool context instead of mandatory fixed values. |
| https://docs.langflow.org/agents-tools | Tools/toolsets may accept Agent-provided inputs; approvals and workflow-as-tool composition reuse general Agent primitives. |
| https://marketplace.dify.ai/plugin/lysonober/browser-use-cloud | An integration may delegate a complete browser task, poll and obtain results. That is a separate architecture from giving the host Agent primitive tools. |
| https://docs.flowiseai.com/integrations/langchain/tools/web-browser and https://docs.flowiseai.com/integrations/langchain/document-loaders/playwright-web-scraper | A component called Browser may only read/extract content; it is not evidence of a general action loop. |
| https://docs.browser-use.com/cloud/quickstart and https://docs.browser-use.com/cloud/which-product | Browser infrastructure, an embedded Agent and hosted task execution are distinct products; task-based entry can omit a separate URL field. |
| https://www.skyvern.com/docs/concepts | Browser task loops coexist with reusable block-based workflows and per-run inputs. |
| https://docs.stagehand.dev/v4/migrations/v3 and https://docs.stagehand.dev/v4/add-ons/search | The surveyed v4 API separates browser operations from the caller's Agent loop; search can discover URLs first. |
| https://developers.cloudflare.com/agents/tools/browser/ | Persisting a browser reference can support continuity while the remote session is alive; expiry/crash is not a durable browser checkpoint. |
| https://github.com/microsoft/playwright-mcp and https://playwright.dev/python/docs/docker | MCP is not a security boundary; running a browser against untrusted sites needs isolation beyond a stock test-container recipe. |
| https://docs.browserless.io/baas/bot-detection/overview and https://developers.cloudflare.com/bots/concepts/bot-score/ | Stealth and IP reputation address parts of bot detection. They do not establish a universal firewall or access-control bypass. |

## Commands

- Initial local allocation occurred on 2026-11-03. Publication on 2026-11-04 followed a fresh fetch and all-ref allocation in a clean worktree at develop 94c44366. Current IDs are REQ-0086, DES-0004, ARCH-0002, DEC-0085, PLAN-0006, DISC-0002 and individually allocated TASK-0241–0253. Original unpublished DEC-0084 / TASK-0238–0250 were renumbered because merged work claimed those IDs.
- Factory execution here uses the existing backend virtualenv interpreter at the path above. The worktree has no local `backend/.venv`; system Python was observed to lack PyYAML. This is a local execution detail, not a delivery blocker or task.
- Declared project checks from `project.md` / `package.json`: backend `.venv/bin/python -m pytest -q` from `backend`; root `npm test`, `npm run build`, `npm run lint`, `npm run test:e2e`; Factory `validate`, `ready`, `verify run --profile full`. These application checks were not executed by this research/planning turn.
- Future fixture filenames/commands in the task set are planned, not observed existing tests.
- Final planning checks: all-ref ID uniqueness passed (95 refs), all 19 new artifact/task sections/references and the 13-task dependency DAG passed, and `git diff --check` passed. `factory validate` exited 1 only for missing local dependency environments/packages; no artifact-structure error reported. No dependencies were installed for this documentation-only request.

## Architecture Observations

- Stateful browsing cannot be implemented safely by assuming the existing generic per-call MCP transport retains a page.
- A generic managed effect replay does not reconstruct the page after a lost browser. Session generation, stale observation and uncertain effects need explicit contracts.
- Connection-level proxy configuration is separate from task URLs. Neither prompt parameters nor website content can change the connection's network authority.
- Existing generic nodes and Agent loop fit the feature. A whole delegated browser Agent is optional later integration work.

## Standards Discovered

- AGENTS.md; docs/backend-architecture.md; docs/ui-conventions.md including typed-name deletion, shadcn/theme tokens, en/vi and the fixed Settings/Data/Execution tabs; shared envelope/error catalog; SQLAlchemy/Alembic; one task PR and explicit owner merge approval.

## Gaps And Unknowns

- Exact provider/proxy protocol/auth matrix, remote egress guarantees, origin-filtered pre-provisioned profile support, search adapter and portable runtime packaging need implementation-time proofs.
- The mockup has no runtime, no network enforcement and no complete export; its extra tabs are exploratory, not production navigation approval.

## Recommended Follow-Up Artifacts

- REQ-0086, DES-0004, ARCH-0002, DEC-0085 and PLAN-0006, all linked in this delivery's plan.

## Amendment note (2026-11-06)

Owner amended the Proposed package without accepting it. Research above remains valid as repository evidence. Product scope changes that affect later proofs: Browserless is the required first remote provider; origin whitelist is mandatory; sessions persist across chat turns of the same conversation; upload/download and evaluate JS are in first delivery with bounds; mutating-approval defaults OFF; executable exports are deferred after studio; draft implementation PRs #303–#315 started against the prior Proposed wording and need reconciliation after acceptance. Reconfirm Browserless docs/capability claims at task-start: https://www.browserless.io and https://docs.browserless.io/ .
