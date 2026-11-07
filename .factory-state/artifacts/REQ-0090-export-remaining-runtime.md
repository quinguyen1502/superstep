# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0090
- Status: accepted
- Owner: Thái Quí Nguyễn
- Created: 2026-11-07
- Updated: 2026-11-07
- Source: Owner message 2026-11-07: skip cross-language code nodes; implement the other TASK-0266 leftovers

## Summary

Python and TypeScript exports run three Studio behaviours that were still placeholders: a model credential per node, human approval with a channel notice, a deadline and AI review, and managed-connection calls. Secrets stay in environment variables. Cross-language code nodes stay out.

## Problem Or Opportunity

An exported file could call MCP, a knowledge base and SMTP, and it could fall back to a second model. It still could not use a different provider key on one node, notify an approval channel, enforce a deadline, review an approval, or call a managed connection. Those steps either mocked, paused for a person with no deadline, or raised a placeholder.

## Scope

### In Scope

- Per-node LLM credential slots for LLM, fallback, attachments, Agent and Decision nodes in both exports.
- Approval export: rule check, judge, daily cap, channel notice, deadline, reminders, escalation wait.
- Managed-connection calls for telegram, slack, whatsapp, teams, http_api, email, google_sheets, google_drive and web, configured from environment JSON.
- Handbook pages in English and Vietnamese.

### Out Of Scope

- Cross-language code nodes (a Python file running TypeScript, or the reverse). The owner declined this on 2026-11-07. TASK-0266 keeps it as declined.
- React Native and Flutter (TASK-0227, TASK-0228).
- Marking REQ-0086 or REQ-0089 done.
- Embedding Studio secrets, channel targets, approver addresses or credential ids in the file.

## Stakeholders Or Users

- A builder who downloads a workflow and runs it with their own keys.
- An operator who configures environment variables and does not want Studio secrets in the file.

## Current Context

- REQ-0089 adapters are on develop. TASK-0266 still listed advanced approval, per-node credentials, managed connections and cross-language code.
- `templates.sanitize` blanks resource ids. Exporters reattach internal keys that are never written out.
- `managed_operation(tool, arguments)` raises `Managed connection placeholder`. An invalid browser connection must keep that placeholder.
- Simple Human nodes call `interrupt` with the node and the question. Agent tool approval builds a fixed question sentence.

## Desired Behavior

- A node with a credential uses `LLM_CRED_<n>` when `<SLOT>_PROVIDER` is set, and otherwise keeps today's `LLM_PROVIDER` behaviour. The credential id is not in the file.
- A Human or Agent approval with a channel, a deadline or an AI-review policy notifies, waits and reviews. A queued example answer returns before any notice. Suggest mode never answers. Auto mode approves only when the judge approves with enough confidence. A reject rule can reject. Anything unsure asks a person.
- A managed connection reads `<PREFIX>_SETTINGS` and `<PREFIX>_SECRETS`, pins targets, does not follow redirects, and journals the outcome. Unconfigured and offline is an announced dry run. Unconfigured and live names the missing variables. Unknown outcomes are not retried.

## Business Rules

- Generated security is not weaker than Studio: pinned addresses, no redirects, private addresses refused unless the existing allow flag is set.
- The Google token URL is fixed. Telegram, Slack and WhatsApp API URLs may use their existing environment overrides.
- Approval webhook URLs are operator environment, called without following redirects.
- Offline (`LLM_PROVIDER` unset, and no slot provider) announces mocks and does not auto-approve.
- Example answers short-circuit before a channel notice or a deadline wait.

## Constraints

- One branch for TASK-0273, TASK-0274 and TASK-0275 because the two exporters are shared.
- Do not implement cross-language code nodes.
- New API error codes are not required: export failures raise in the generated process.
- UI strings in the handbook stay in both locales.

## Acceptance Criteria

- Two credentials become two slot names. The ids are absent. A set slot provider is used. An unset slot still uses `LLM_PROVIDER`.
- An auto-mode reject rule answers rejected without asking. A deadline fires its action. A configured channel receives one local POST when the run really waits. Secrets and approver addresses are absent.
- A telegram export posts to a local API when settings are in the environment, dry-runs when they are not and the run is offline, and does not retry an unknown status. The server id and secrets are absent. An invalid browser connection still raises the placeholder and does not call `browser_call`.
- English and Vietnamese handbook rows describe the three behaviours.

## Edge Cases

- A policy that fails validation is not reviewed: a person is asked.
- A deadline that is not a duration is omitted and its addresses are not written.
- A managed call without a prefix still raises the placeholder, including a browser connection with invalid settings.
- The approval journal cannot be written: the run does not auto-approve.
- The same managed key with different arguments conflicts. The same key and arguments return the stored result.

## Assumptions

- The owner accepted this requirement by asking to do the remaining parts except cross-language code (2026-11-07).
- Optional slot fallback to `LLM_PROVIDER` keeps existing exports working when only `LLM_PROVIDER` is set.

## Open Questions

- None. Cross-language code is declined. The other three parts are accepted.

## Related Artifacts

- `.factory-state/decisions/DEC-0089-export-remaining-runtime.md`
- `.factory-state/artifacts/PLAN-0010-export-remaining-runtime.md`
- `.factory-state/tasks/backlog/TASK-0266-export-remaining-gaps-proposal.md`
- `.factory-state/artifacts/REQ-0089-export-parity-adapters.md`
