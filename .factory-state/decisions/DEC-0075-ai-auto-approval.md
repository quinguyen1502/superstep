# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0075
- Status: Accepted. The owner approved decisions 1 to 8 and the recommended answer to every open question on 2026-10-30. Planned on 2026-10-30 (TASK-0186 to TASK-0189).
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Related Requirements: REQ-0081, REQ-0041, REQ-0072, REQ-0073
- Related Tasks: TASK-0186, TASK-0187, TASK-0188, TASK-0189
- Related Architecture: DEC-0019 (approval channels), DEC-0063 (Agent node, tool approval), DEC-0039 (Decision node), DEC-0009 (layers)

## Context

- Approvals today:
  - a Human node or an approval-gated Agent tool raises `Interrupt`;
  - `ApprovalService.on_waiting` notifies channels;
  - an answer is recorded with compare-and-set, audited, and resumes the run;
  - `fire_deadlines` already answers for people on timeout.
- LangGraph resumes an interrupt with `Command(resume=value)` from outside the graph, so any trusted caller can answer (https://docs.langchain.com/oss/python/langgraph/interrupts).
- Prior art:
  - LangChain `HumanInTheLoopMiddleware`: `interrupt_on`, `allowed_decisions`, and a `when` predicate per tool (https://docs.langchain.com/oss/python/langchain/human-in-the-loop).
  - Copilot Studio AI approval stages: approve or reject with a rationale; an undecided request goes on to the next human stage (https://learn.microsoft.com/en-us/microsoft-copilot-studio/flows-advanced-approvals).
  - UiPath tool guardrails: deterministic rules with Block or Escalate (https://docs.uipath.com/agents/automation-cloud/latest/user-guide/tool-guardrails).
  - OpenAI Agents SDK: `needs_approval` as a callable that fails closed (https://openai.github.io/openai-agents-python/human_in_the_loop/).
  - PydanticAI `ApprovalRequired` (https://pydantic.dev/docs/ai/deferred-tools/).
  - OWASP LLM06 Excessive Agency: approval enforced outside the LLM (https://genai.owasp.org/llmrisk/llm062025-excessive-agency/).
- Verbalized LLM confidence is often overconfident (arXiv 2306.13063), hence suggest mode first and a threshold treated as only one signal.

## Decision

1. **Where it runs.** A new `AutoReviewService` is called by `ApprovalService.on_waiting` before any channel message, with the same input for Human nodes and Agent tool steps.
   - Outcomes: `approved`, `rejected` (rule only), `escalated` or `suggested`.
   - An approve or reject outcome reuses the deadline auto-answer path:
     - record the answer with compare-and-set as actor `auto`;
     - enqueue `resume` with the same value a person sends;
     - close or edit the waiting messages;
     - notify the owner.
   - An escalation continues the normal `on_waiting` flow with the opinion attached.
   - The engine and graph do not change.
2. **Config placement.** `approval.auto` inside the existing `approval` object, which both the Human node and the Agent node already use (`agents.expand` copies it onto tool steps). One validator lives in `engine/approval_policy.py` (pure, no I/O), next to `deadlines.py`.
3. **Judge.**
   - A separate call through `engine/providers` with its own credential, model and fixed system prompt. The builder's instructions are added as policy.
   - The request goes in a delimited data block marked untrusted. The prompt never includes the agent's system prompt or messages.
   - Structured output (JSON schema): `{decision, confidence, reason, flags[]}`. Anything off-schema means escalate. Temperature 0, 30 s timeout, usage recorded.
   - The judge has no tools.
4. **Rule language.** Simple field conditions `{field, op, value, effect}` with a fixed operator list. No expression language in the MVP; KISS, and safe to show in the UI. Fields are dot paths into the tool arguments or the state.
5. **Defaults.**
   - `mode` off (the editor preselects suggest when turned on);
   - `min_confidence` 0.8;
   - `max_per_day` 50 per workflow per day;
   - the judge's reject means escalate;
   - errors escalate;
   - mock, test run and demo never approve;
   - `notify` on.
6. **Suggest mode.**
   - The channel message and the Approvals inbox show "AI suggests: <decision> (<confidence>) — <reason>" above the buttons.
   - The human's answer is compared and stored as agree or disagree.
   - This builds the evidence for turning auto on.
7. **Audit and metrics.**
   - `ApprovalAudit` gains nullable columns `auto_outcome`, `auto_confidence`, `auto_model`, `auto_reason`, `policy_hash` and `agreed` (one Alembic revision).
   - Approvals page metrics are computed by querying the audit, so there is no separate metrics table.
   - Kill switch:
     - per workflow: a workflow setting `auto_approval_paused`;
     - per organisation: an admin setting, plus the `STUDIO_AUTO_APPROVAL` operator variable.
8. **Export.** Graph unchanged. A note in each exporter, like channels and deadlines. Exported rules are a later phase.

## Rationale

- Running inside `on_waiting` keeps one place for every approval source and reuses a proven auto-answer path with audit, so no new engine semantics are needed.
- Deterministic rules before an LLM follow UiPath, OpenAI and OWASP guidance. The LLM can only narrow toward people, except a confident approve that passed every rule.

## Alternatives Considered

- **A new "AI Review" node on the canvas** (Decision → Condition → Human): visible in the graph and exportable, but it does nothing for Agent tool calls, and it duplicates audit and notification. Not chosen.
- **A policy inside the engine before raising `Interrupt`** (like LangChain's `when`): no wait record and no inbox entry for suggest mode, and the LLM call would sit in the engine's step and be repeated on resume. Not chosen.
- **An expression language** (JSONLogic or Python-like) for rules: more power, harder to validate and show. Later, if needed.
- **The Decision node's Jev as the only judge**: typed probabilities are attractive, but tie it to one provider. Not chosen; any configured chat credential can be the judge (owner decision 4).

## Impacts

- New service and engine module, Alembic revision on `approval_audit`, workflow and admin settings, new error codes, UI in Human and Agent settings and in Approvals, handbook pages, export notes.

## Risks

- Overconfident judges, which suggest mode, the threshold, the cap and the kill switch mitigate.
- Prompt injection in the reviewed content, which rules first, delimited data, no tools, escalate on a flag and the handbook warning mitigate.
- Owners trusting auto too early. The editor shows suggest-mode agreement before enabling auto.

## Owner Decisions

The owner approved the recommended answer to every question on 2026-10-30.

1. **Default `min_confidence`**: 0.8. The editor shows the AI/human agreement rate from suggest mode next to the setting.
2. **Auto-reject**: only rules (effect `reject`) can reject. The AI judge never auto-rejects; its reject escalates to people.
3. **Who can enable**: only the workflow owner and admins can set `mode: auto`; any editor can set `suggest`.
4. **Judge models**: any configured chat credential can be the reviewer model.
5. **Cap scope**: `max_per_day` counts automatic answers per workflow per day.
6. **Delay and undo**: not in the MVP; it stays in the later phase.
7. **Notification target**: only the run owner is notified of automatic answers.

## Approval

- Approved By: Thái Quí Nguyễn
- Approved On: 2026-10-30
- Scope And Limits: Decisions 1 to 8 and the owner decisions 1 to 7 as written, for the MVP in REQ-0081. Tasks are not planned yet; the task set needs the owner's confirmation.

## Review Or Revisit Trigger

- The human override rate on auto-approvals exceeds a set level.
