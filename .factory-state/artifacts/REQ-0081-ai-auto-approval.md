# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0081
- Status: Accepted on 2026-10-30 with the DEC-0075 owner decisions (all recommended options). Not planned into tasks yet.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Source: owner idea in chat on 2026-10-30 ("cho phép dùng 1 llm/agent để auto approve và chỉ thông báo về cho owner, vẫn có chấm điểm confident và các rule như chỉ duyệt theo khung giờ, ko quá max số lượng, có chứa 1 số thông tin gì đó"). The owner said the rule ideas are examples only. Research: Copilot Studio AI approval stages, UiPath tool guardrails, OpenAI Agents SDK `needs_approval`, LangChain `HumanInTheLoopMiddleware` (links in DEC-0075).
- Related Decision: DEC-0075 (Accepted)

## Summary

- An approval (a Human node, or an Agent node tool marked `approval: true`) can be **reviewed by AI first**:
  - deterministic field rules run first;
  - then a separate LLM judge returns approve, reject or escalate, with a confidence and a reason.
- In **auto** mode, a confident approval answers the request the same way a person would, and the owner is notified afterwards.
- Everything else goes to the usual people, with the AI's opinion shown.
- In **suggest** mode (the default when enabled), the AI only shows its opinion and never answers.

## Problem Or Opportunity

- Routine approvals (small refunds, standard replies) wait for a person even when the answer is obvious. That slows runs, and people learn to click Approve without reading.
- Building an "AI pre-check" today needs a Decision node, a Condition and a Human node by hand. That gives no approval audit, no owner notification, no inbox entry, and nothing for Agent tool calls.
- Microsoft Copilot Studio ships AI approval stages. UiPath, the OpenAI Agents SDK and LangChain ship rule-based pass-or-escalate hooks. Visual builders in Superstep's space (n8n, Dify, Flowise, Langflow) document human review only.

## Scope

### In Scope (MVP)

- **Settings** `approval.auto` on the Human node and on the Agent node's approval settings (one shape for both):
  - `mode`: `off` | `suggest` | `auto`. Off by default. Suggest is preselected when the builder turns it on.
  - `rules`: a list of `{field, op, value, effect}`, where `effect` is `human` (send to people) or `reject`.
  - `max_per_day`: a cap on auto-answers per workflow per day.
  - `judge`: `{credential_id, model, instructions}`.
  - `min_confidence`: 0 to 1, default 0.8.
  - `notify`: default on.
- **Rules**: simple field conditions on the request:
  - for a Human node, state fields that the prompt template reads;
  - for a tool, the tool name and arguments.
  - Operators: equals, not equals, contains, not contains, matches (regex), greater than, less than, is empty.
  - A rule that matches applies its effect. No match lets the judge decide. Rules never auto-approve on their own.
- **Judge**: a separate model call, never the agent being reviewed. It gets:
  - the builder's instructions;
  - the request as delimited data;
  - for a tool, the tool name and description, and the arguments.

  It must return structured output `{decision: approve|reject|escalate, confidence, reason}`.
- **Outcome in auto mode**:
  - **auto-approve** when the judge approves, confidence ≥ `min_confidence`, no rule sent it to a person, and the daily cap is not reached;
  - **auto-reject** only when a rule with effect `reject` matched. The judge's reject escalates by default; there is no auto-reject from the judge in the MVP;
  - otherwise **escalate**: the usual channels, approvers and deadline, with the AI's decision, confidence and reason shown.
- **Fail-safe**: any of the following escalates and never approves:
  - judge error or timeout;
  - unparsable output;
  - missing credential;
  - cap reached;
  - kill switch on;
  - the judge reporting a suspected instruction in the content (an `escalate` with reason `injection`).
- **Answering**: an auto-answer uses the same path as the deadline auto-answer (TASK-0066):
  - the answer is recorded once (compare-and-set);
  - the run resumes with the same value a person would send (`approved` or the rejection text);
  - waiting messages are edited.
- **Audit**: one `ApprovalAudit` entry per auto-review, with actor `auto`, the outcome, the policy version (hash of `approval.auto`), the model, the confidence, the reason and the rules that matched. Suggest mode is audited too.
- **Owner notification** (run owner only) through the existing notifier and channel: "Auto-approved by AI (0.92): <reason>", with a link to the run.
- **Approvals page**:
  - an "AI" badge on auto-answered and suggested items;
  - per-workflow counts (auto-approved, escalated, and in suggest mode how often people agreed);
  - a **kill switch** per workflow, plus an organisation-wide one for admins.
- **Demo and offline**: the offline mock judge, test runs (TASK-0067) and demo mode never auto-approve; they escalate. Suggest still shows the mock's opinion, labelled as a mock.
- **Roles**:
  - any builder who can edit the workflow can set `suggest`;
  - `auto` needs the workflow owner or an admin;
  - an admin can turn auto-approval off for the organisation (`STUDIO_AUTO_APPROVAL=off` also disables it for the operator).
- **Export**: the graph is unchanged (the interrupt stays). Python, LangGraph project and TypeScript exports add a note that AI auto-review is a Superstep feature, as they do for channels and deadlines.
- **Errors** in the common envelope: new codes in `core/errors.py` CATALOG, `docs/api-errors.md` and both locales. Examples: `AUTO_APPROVAL_FORBIDDEN`, `AUTO_APPROVAL_RULE_INVALID`, `AUTO_APPROVAL_JUDGE_REQUIRED`, `AUTO_APPROVAL_DISABLED`.
- **en and vi** UI strings. Handbook en and vi: the Human node and Agent node pages, plus an "AI review of approvals" guide with the risks. CHANGELOG.

### Later (not MVP)

- Spot-check sampling: a share of would-be auto-approvals still goes to people.
- Auto-disable after N human overrides or disagreements in a period.
- Time windows (auto only within set hours and time zone).
- Sum caps (for example, the total amount per day of a numeric argument).
- A delay before resuming, with an "Undo" button in the notification.
- A sub-workflow as reviewer.
- Calibration reports (confidence against human answers from suggest mode).
- Export helpers that run the rules in exported code.

### Out Of Scope

- Letting the agent approve its own call.
- Auto-edit of tool arguments (LangChain `edit`). An AI cannot change what runs.
- Auto-answers to free-text Human questions that are not approve or reject.

## Stakeholders Or Users

- Workflow owners with frequent routine approvals.
- Approvers, who see fewer and better-prepared requests.
- Admins who govern automation.

## Current Context

- `services/approval_service.py`:
  - `on_waiting` sends channel messages;
  - `decide`, `decide_link` and `answered_in_studio` record answers with compare-and-set, queue `resume` and audit;
  - `fire_deadlines` already auto-answers (`deadline_approved` / `deadline_rejected`).
- `engine/deadlines.py` (REQ-0041); the Approvals inbox (`frontend/src/pages/Approvals.tsx`).
- `engine/agents.py` (REQ-0072, TASK-0117): tool approval pauses like a Human node and reuses `approval` and `deadline`.
- `engine/decisions.py` (Decision node, DEC-0039) is a typed classifier, not an approval feature. The judge can reuse providers, but not the node.

## Desired Behavior

1. A refund agent calls `refund(amount=20, reason="duplicate charge")`. Rules: `amount > 100 → human`. The judge approves at 0.93 (≥ 0.8). The tool runs at once, and the owner gets a Telegram message "Auto-approved by AI (0.93): duplicate charge under policy". The audit shows actor `auto`.
2. The same agent calls `refund(amount=500)`. The rule matches, so the approvers get the usual message plus "AI: rule amount > 100 → sent to people".
3. The judge's model is down. The request escalates with "AI review failed: timeout", and the run waits as before.
4. Suggest mode: the approver sees "AI suggests: approve (0.88), reason …" next to the buttons, and their answer is counted as agree or disagree.
5. An admin turns on the kill switch. New requests go straight to people, and the editor shows auto-approval as paused.

## Business Rules

- Precedence: kill switch, then rules, then the cap, then the judge, then the threshold. Every non-approve outcome escalates, except a rule with effect `reject`.
- The judge never sees the reviewed agent's system prompt or reasoning as instructions, only the request data.
- An auto-answer counts as an answer by `auto`. The run owner is notified even if they are not an approver.
- After a human or auto answer, later answers get `APPROVAL_ALREADY_DECIDED` (unchanged).

## Constraints

- DEC-0009 layers. Settings live in node JSON, so no new table for them. Audit columns or metrics may need an Alembic revision (DEC-0075). No new dependency.
- The judge call has a timeout (default 30 s) and counts in usage like other LLM calls.

## Acceptance Criteria

- With a mock judge returning approve at 0.9 and `min_confidence` 0.8, in auto mode with a real (non-mock) credential stubbed in the test, a Human node run resumes with `approved` without a human answer. The audit has actor `auto`, the model, 0.9, the reason and the policy hash, and the notifier was called once.
- The same request with confidence 0.7 escalates: the channel message is sent and contains the AI opinion.
- A matching `human` rule escalates even when the judge approves. A matching `reject` rule resumes with a rejection without calling the judge.
- A judge exception, a timeout, invalid JSON, or decision `escalate` each escalates. No approval happens (one test each).
- After `max_per_day` auto-answers in a workflow, the next request escalates with reason `cap`.
- The mock judge, test runs and demo mode never auto-approve (tests).
- Agent tool approval: an auto-approved call runs the tool, and an escalated one pauses as today (engine test).
- Suggest mode never resumes a run. The answer records agree or disagree, and the Approvals page shows the counts.
- A non-owner editor saving `mode: auto` gets `AUTO_APPROVAL_FORBIDDEN`. Invalid rules get `AUTO_APPROVAL_RULE_INVALID`. Both are translated in en and vi.
- The kill switch (workflow and organisation) makes new requests escalate (test).
- Exports are unchanged apart from the note (snapshots).
- The backend suite, vitest, e2e (suggest badge and auto badge in en and vi), `tests/test_layers.py`, `tests/test_api_envelope.py` and the strict handbook build pass.

## Edge Cases

- Several tool calls in one wave: each is reviewed on its own, and the cap counts each.
- An approval inside a workflow tool's child run uses the child node's policy. The notification names the chain (TASK-0135).
- The policy changes while a request waits: the request keeps the review it got. The policy hash is in the audit.
- A deadline and auto both apply: the auto-review happens first. If it escalates, the deadline runs as today.
- The content tells the judge to approve: the judge prompt treats content as data. Rules run first; prompt injection is a stated risk in the handbook.

## Assumptions

- The judge uses the existing provider credentials (OpenAI, Anthropic, OpenRouter, compatible). Any configured chat credential can be the judge (owner decision 4).

## Owner Decisions

The owner approved the recommended answers on 2026-10-30. They are recorded in DEC-0075 "Owner Decisions":

1. Default `min_confidence` 0.8. The editor shows the AI/human agreement rate from suggest mode.
2. Only rules may reject. The AI judge never auto-rejects.
3. Only the workflow owner and admins can turn on `auto`. Editors can turn on `suggest`.
4. Any configured chat credential can be the reviewer model.
5. The daily cap counts per workflow per day.
6. No undo delay in the MVP (later).
7. Only the run owner is notified of automatic answers.

## Open Questions

None. The DEC-0075 questions are answered.

## Related Artifacts

- `.factory-state/decisions/DEC-0075-ai-auto-approval.md`
- `.factory-state/artifacts/REQ-0003-human-in-the-loop.md`, `REQ-0034-more-approval-channels.md`, `REQ-0041-approval-deadlines-and-inbox.md`, `REQ-0072-agent-node.md`, `REQ-0073-agent-workflow-tools.md`, `REQ-0036-jev-decision-node.md`
