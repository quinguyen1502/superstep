# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0084
- Status: Accepted on 2026-11-03; owner approved PR #292 ("Duyệt")
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-03
- Related Requirements: REQ-0082
- Related Plan: PLAN-0002
- Related Tasks: TASK-0229, TASK-0230; TASK-0227/0228 deferred by owner
- Related Decisions: DEC-0052/0054 (chat/history/Human), DEC-0057 (run time travel), DEC-0067 (published chat), DEC-0072/0074 (files), DEC-0077/0078/0079 (identity, v1, shared UI)

## Context And Observed Constraints

The owner requested prioritising edit/regenerate for 0.11.0 and temporarily deferring native TASK-0227/0228. Web TASK-0223–0226 is integrated through #288–291; develop is 02361fbd. This changes release grouping from the original PLAN-0002 recommendation. Native acceptance is deferred, not completed or cancelled.

`ChatSessionService.prepare/history/write` builds one workflow run per root user message, with a bounded history window. Human answers are also persisted as user turns, but resume the existing run. Sessions retain active-agent handoffs. Files belong to one session/turn; external storage keys include the session, and deletion/retention removes its objects. Ratings and run steps refer to saved turns/runs.

`RunService._plan_fork` implements DEC-0057 node-level time travel for Studio users. It requires a forkable, untruncated trace checkpoint, rejects imported graphs, and permits state editing. It is not a general public chat revision API. Exposing it directly would also bypass the public session ownership and bounded-input boundary.

## Decision

### Conversation semantics

1. Both actions create an independent chat session owned by the same principal and under the same chat/channel. Keep source turns, answers, ratings and runs unchanged. Store optional lineage (source session/turn and action), with no dependency that makes a branch unreadable after source deletion or retention.
2. **Edit:** allow a root user message, including an older one, in a settled conversation. Copy the prefix before that message, append the edited message, and generate a new answer. Later source messages are excluded from the branch. Human responses are not editable root messages; the UI explains this distinction.
3. **Regenerate:** allow the latest terminal assistant answer and rerun its initiating root message with the prefix before that root message. Terminal errors/cancellations may be retried this way. A waiting Human/reviewer question is not a terminal answer. Prior Human responses in that run are not silently replayed; the new attempt asks again.
4. Reject both actions while the source has a queued/running/waiting/paused operation. Recheck eligibility at admission on the server, including stale source/turn checks. An invalid request creates no visible branch and starts no run.
5. Select the new branch on success. Keep the original available in history with an authorised link back when it still exists. Version 0.11.0 uses this explicit branch model; an inline answer-version carousel is not part of these tasks.

### Execution and side effects

6. Run the initiating message through the existing chat message pipeline, from the start of the **currently saved/published workflow**. Rebuild history and the active-agent selection from the retained prefix, never from the discarded source suffix. Do not expose arbitrary checkpoint/state/run selection to public clients. This reuses normal input validation, resource resolution, approvals, attachment admission and streaming.
7. A revision is a fresh user-authorised execution. It may call tools, write data or send notifications again; it is not an undo or a model-only rewrite. Before submitting either action, show an en/vi confirmation explaining that the workflow runs again and external actions may repeat. Cancelling the dialog changes nothing. Existing Human and reviewer approvals still apply independently.
8. Use a caller-generated operation ID scoped to the authenticated principal and source session. Enforce durable uniqueness and atomic admission with the source eligibility check. Repeated delivery/reconnect of the same intent returns its branch/run outcome and never starts another run. A distinct intentional operation gets fresh normal run/effect keys and consumes normal quotas. Unknown interrupted outcomes are recovered by reading persisted state, not by resending execution.

### History, files and lifecycle

9. Materialise retained prefix turns with fresh IDs and mark them inherited/read-only. Preserve history text and allowed step visibility; inherited turns cannot answer an old Human question or create another rating/feedback job. Source ratings remain attached to source turns/runs. New generated turns have their own feedback lifecycle.
10. Copy retained and initiating-message attachments to independent IDs/storage objects using the existing attachment storage boundary. Remap turn IDs and never share a deletable fs/S3 object key between sessions. Keep current file/type/size permissions and use bounded streaming/staging; do not load an entire conversation's bytes into memory. A missing/unreadable required file fails preparation rather than silently dropping it.
11. Stage file objects before atomic publication of the branch, its prefix and operation record. On failure, clean staged objects through existing compensation/orphan handling; do not leave a partially usable branch or start its run. Source deletion and branch deletion/retention must not corrupt each other's history/files. Parent lineage becomes unavailable gracefully; deleting a branch keeps the existing typed-name confirmation.

### APIs, SDKs and UI reuse

12. Add explicit edit/regenerate operations to public v1 and Studio chat admission. Keep existing message/answer behaviour unchanged. Discover support through additive capability fields; older servers/clients continue existing chat and unsupported actions fail clearly. Specify request/operation IDs, branch session IDs, persisted recovery and streamed completion in the socket schema/AsyncAPI and generated SDK contracts before implementing consumers.
13. Carry the selected branch session ID through run-start/completion/recovery, so every history fetch, Human answer, upload and rating addresses the branch. Apply published access, app-key revocation, origin checks, per-user/IP/daily limits and principal isolation before returning lineage or claiming an operation. A fork grants no additional permission.
14. TASK-0229 delivers the shared branch/admission foundation, edit operation, TypeScript/Python helpers, shared React/Studio/public/widget editing, en/vi docs and acceptance coverage. TASK-0230 depends on its merged foundation and adds regenerate through those same layers. No duplicate transport or UI implementation. Use shadcn/theme tokens, accessible labelled actions, edit/save/cancel states, keyboard operation and actionable localised errors. Screenshots stay outside Git.

## Alternatives Considered

- Mutate/delete source turns: simpler display, but loses audit/history, changes rated answers and races with active runs. Rejected.
- Reuse node checkpoint time travel directly: can skip earlier nodes, but checkpoint availability/trace truncation/import limits and public state access do not match general chat editing. Retain the existing Studio debugging feature separately.
- Share ancestor rows/files through a new conversation graph and reference-counted storage: saves copying, but changes retention/deletion and permission semantics across all existing sessions. Defer until measured branch storage costs justify it.
- Regenerate only an inferred final LLM node: arbitrary workflows can form answers through several nodes/tools. This cannot honestly guarantee a pure text rewrite; use the explicit rerun contract.

## Acceptance And Validation

- SQLite/Postgres: atomic branch creation/admission, duplicate operation IDs, concurrent source changes, durable recovery and crash boundaries; no duplicate run/effect from one intent.
- Authentication: anonymous, Studio and third-party identities; cross-user/chat/turn IDs, stale origins, revoked keys and expired-token refresh cannot create/read another user's branch.
- Edit an early message: branch sees only its prefix plus edited text; source remains unchanged after reload. Reconstruct handoff state from that prefix. Human answers are rejected as targets and busy sessions cannot fork.
- Regenerate the latest answer/error: source stays intact; one new run/answer belongs to the selected branch. Human/reviewer prompts are newly answered/approved. Existing quotas and cancellation remain effective.
- Files on db/fs/S3: independent IDs/objects, missing-file refusal, storage failure cleanup and either session's deletion/retention leave the other usable. Inherited ratings cannot duplicate feedback.
- Public OpenAPI/socket/AsyncAPI and generated contracts remain additive; TypeScript store/React and Python sync/async cover branch IDs, recovery and unsupported servers.
- Browser acceptance: Studio, public page/widget and the existing cross-origin host on React 18/19; edit/save/cancel, rerun confirmation, branch navigation, identity switching, Human/file/feedback flows, en/vi and light/dark screenshots outside Git. Full declared Factory profile and applicable CI pass per task.

## Risks And Release Scope

Forking copies retained data and uses additional storage. Rerunning may repeat deliberate external effects; the explicit confirmation and intent deduplication address different concerns and neither promises external rollback. Workflow changes can change the answer; the UI/docs state that the current saved/published workflow runs. Storage publication and admission races require focused failure/concurrency tests before acceptance.

Target 0.11.0: integrated generic adapters/events and chat phases 1–3 plus approved TASK-0229/0230. Keep shared Python SDK/CLI/server versioning; bump to 0.11.0 in release preparation after feature integration. TypeScript/React retain their independently approved version scheme. Native TASK-0227/0228 stays deferred, and REQ-0082 is not claimed fully complete. Release preparation must verify version pins, migrations, package contents, en/vi guides, changelog and full CI. Merge/release tags and registry publication require the owner's explicit release instruction on the concrete validated result.

## Approval

- Approved By: Thái Quí Nguyễn (PR #292, "Duyệt")
- Approved On: 2026-11-03
- Scope already authorised: prioritise TASK-0229/0230 for 0.11.0 and defer TASK-0227/0228.
- Accepted scope: branch, rerun, file lifecycle and UI/API semantics above. TASK-0229 implementation is authorised on the existing PR; TASK-0230 follows the shared foundation on a separate PR. No merge or release is authorised by this design acceptance.

## Revisit Trigger

Measured branch storage costs, a concrete requirement for model-only regeneration, editing Human responses, inline version navigation or pinned historical workflow execution.
