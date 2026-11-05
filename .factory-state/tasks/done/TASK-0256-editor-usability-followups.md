# Task

## Metadata

- Project: superstep
- Task ID: TASK-0256
- Status: done
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-05
- Requirement IDs: owner-reported post-0.11.1 editor follow-ups
- Architecture IDs: DEC-0008, DEC-0055

## Objective

Address the owner's two screenshot batches together: editor layout, useful empty dropdowns, state-field quick actions and immediate chat-run visibility without reloading Studio.

## Acceptance Criteria

- Batch 1 image 1000010914: node drag preview has no extra rectangular corners/background beyond the rounded card.
- Batch 1 image 1000010913: time-travel step list and state viewer align; remove or relocate the redundant State heading without losing an accessible name.
- Batch 1 image 1000010910: empty dropdowns visibly open with a translated empty state instead of appearing unresponsive. Distinguish loading/error/empty where existing data flows support them.
- Batch 1 image 1000010915: audit shared warning/error icon-text alignment and affected call sites, including multiline text, rather than adding local offset fixes.
- Batch 1 image 1000010911: dialog header/footer stay fixed; only the body scrolls, including Chat settings on narrow/short screens. Preserve keyboard access and focus visibility.
- Batch 2 image 1000010912: version Restore button has balanced icon/text spacing and padding.
- Batch 2 image 1000010916: attached Palette/State schema and Config panel tab groups have no box shadow; keep keyboard focus indication and active-tab border.
- General tab gains useful existing node information rather than decorative filler or duplicated editable settings. Keep the four-tab contract and meaningful type-specific content.
- State-selection surfaces provide a quick action to explicitly add an eligible state field and select it immediately. Reuse schema editing/validation, respect viewer/read-only access, avoid silent schema mutation, retain undo/dirty-state behaviour.
- Starting a chat makes its run appear in the workflow run log without application refresh; update status during/after execution through existing authorised events where possible. Preserve run selection, filters and workflow isolation; no duplicate rows or leaked visitor/private-session access.
- en/vi, light/dark, keyboard accessibility and desktop/mobile layouts remain supported; use shared shadcn components/theme tokens only.

## Inputs And Related Artifacts

- vision.md, project.md, roadmap.md, project-specs.md (preserve approval statuses)
- docs/ui-conventions.md (especially rules 11 and 12)
- .factory-state/tasks/done/TASK-0254-keep-chat-feedback-actions-aligned-on-mobile.md (prior fixes and preview-before-validation process)
- Owner's 2026-11-05 batch 1 and batch 2 images and instructions, attached in conversation; screenshots are reference evidence, not repository assets.

## Constraints And Out Of Scope

- Owner requested collecting batch 1 and waiting until batch 2 before implementation; both are now received.
- Prepare source preview for owner approval before full tests/build/lint, test edits or CI/push. Do not claim QA based only on preview.
- No new package, backend access expansion, speculative General fields, migration, release/version bump, merge, tag or deployment is authorised by this request.
- Keep screenshots and generated evidence outside Git. Native TASK-0227/0228 remains deferred.
- Factory task-start requires a context handoff and next owner instruction before implementation.

## Validation Plan

After preview approval, adapt/add focused UI regression coverage for drag preview, empty menus, time-travel alignment, shared alerts, bounded-dialog scrolling, Restore, shadow-free panel tabs, explicit state creation and chat-run insertion/status updates. Run root npm test/build/lint and applicable Factory checks; backend layers/envelope and focused backend tests if that code changes. Capture light/dark and en/vi evidence outside Git. Review and QA precede Ready/done; merge needs explicit owner approval.

## Assumptions And Open Questions

- Quick actions mean explicit in-place state creation plus selection, not an automatic field created merely by opening a picker.
- General information will come from actual node metadata/graph relationships; inspect available data before choosing fields.
- Owner explicitly confirmed that realtime includes public-page and other-tab chats. Reuse the existing Redis/in-memory notification fan-out hub for workflow history invalidations; keep all actual reads under existing history permissions.

## Activity Log

- Owner explicitly instructed “Merge và phát hành lên 0.11.2”. This approves the implementation and merge of existing PR #305, plus the necessary checked release sequence for 0.11.2. Move this task to done on the same PR, squash to one commit, rerun final checks and wait for exact-head CI before merging. Source completion is not itself a publication claim. The prior reviewed head 763432b2 passed all 22 executing checks (GHCR publication correctly skipped on a PR), including Postgres 17/Redis 7, all three Playwright shards and Docker/image security smoke. Release metadata/tag/publication work follows integration as its own bounded release task.
- Final validation after owner-authorised fixes: canonical Factory 8/8 passed on source 7c7fc06a / documentation checkpoint 8abb6ac4 (backend 447.23s, unchanged 900s timeout). Independent backend 1194 passed / 66 skipped in 463.23s; focused backend 56 passed / 1 skipped; Redis/RESP2 8 passed / 1 skipped including separate-process publisher; selected UI 22 passed; runtime UI 3 passed with 2 opt-in handbook capture skips. REV-0231 re-review approves for QA; QA-0231 passes with native-device/Redis-7 follow-ups. Earlier failure history stays in both artifacts. Factory evidence/structure validation and diff checks pass. Prepare one Draft PR for owner review; no Ready/done, merge or release authority inferred.
- Owner instructed “Xử lý đi” after the validation failure report: authorises fixing findings 1–3 in this same task, updating regression tests and rerunning validation/review/QA/PR preparation. No merge or release. AnyIO task-group lifetimes replace detached observer tasks; Redis pub/sub closure is shielded from parent cancellation. Display-only live_history snapshots now persist socket run start/resume and node boundaries without enabling queue checkpoint/replay; memory startup recovery cancels orphan display snapshots instead of reexecuting side effects. Tests add a gated public runtime before completion, subscriber cleanup, non-replay recovery and optional separate-process Redis publication. Shadow coverage checks visible paint and keyboard outline rather than one CSS serialization. A /private/tmp Node wrapper explicitly selects arm64 for Python-spawned npm; no dependency or lock change.
- Owner approved the preview with “Ok duyệt” after the runtime/run-log explanation. This authorises validation, targeted regression additions, review/QA and PR preparation for the current diff; no merge or release. The approved uncommitted source is included in the validation checkpoint.
- 2026-11-05: Received all two-batch feedback. Clean working tree; fetched all refs and allocated TASK-0256 with factory ids next TASK --all-refs. Task branch starts at origin/develop 3c83262a. No implementation, tests or publication performed.
- Factory ready exits 0 with the approved todo task. Moved to doing under task-start; source edits remain pending the next owner instruction, as that skill requires.
- Owner instructed “Triển khai”. Implemented the two batches locally using scoped-change, without tests/test edits, build/lint/typecheck, CI/push, merge or version changes.
- Shared Alert now aligns the icon with the first content row and explicitly places descriptions in the second column; removed its legacy translation and the sm Button icon offset. Panel Tabs remove shadows/focus rings in favour of an inset keyboard outline and active bottom border. Native palette drag gets a clipped, ring/shadow-free dedicated snapshot. Time-travel State heading is accessible-only, with the edited badge in the footer.
- Added DialogBody and explicit bounded flex layouts for Chat settings, Versions, Credentials, Templates gallery/save, Import and Transfer; existing already-bounded Run/Test/API/Schedule/trigger/history dialogs keep their structure. Headers/footers cannot shrink; control focus rings have room inside the body viewport.
- Studio SelectContent supplies a visible translated empty state (including empty fragments/groups), with loading/error text for MCP, Retriever and Subgraph lookups. General now shows the existing node description and incoming/outgoing connections with navigation; no new persisted node fields.
- Shared StateFieldAction/StateFieldPicker performs explicit named/typed creation in the existing editor schema, selects the field in the same render and preserves graph-history/dirty tracking. Integrated node outputs, Agent/history/steps, loop fields, Condition, Decision/Email results, model attachments, input fields and template insertion. Chat settings/file field quick actions explicitly disclose “Save workflow & settings” when the workflow draft must be saved first; no silent schema persistence.
- Chat socket events immediately insert/update the current Studio chat in history. Public/tab-independent updates use /ws/workflows/{wid}/runs through NotificationHub's existing Redis or single-process memory implementation. Push has no run contents/identifiers; service checks workflow/run visibility before each invalidation, route rechecks account/token/access on pushes and heartbeats. Progress and terminal records publish only after their existing database writes. Client batches refreshes, resyncs on reconnect/focus, has disconnected polling fallback, ignores stale workflow/request responses, and preserves selected run/test filtering. No migration or access expansion.
- Source-mode preview uses direct Vite (:15556) and API (:18556) with isolated /private/tmp/superstep-0256-preview.db, mock LLM and configured STUDIO_PUBLIC_URL for that local proxy. Initial public POST rejection was the preview's missing external origin configuration; corrected configuration, without weakening origin checks. This is not evidence of the root cause on the owner's unknown deployment.
- Captures are outside Git at /Users/quinguyen/.codex/visualizations/2026/11/01/01a195e9-0003-7e42-9d10-1203ca6438a9/superstep-review-0256. Initial screenshots cover empty run picker, General, state creation, Versions/Restore, Studio chat history, time travel and fixed Chat settings body in light/dark. Preview found a missing Button import in new General content; corrected before final capture. Screenshots are owner-review evidence, not automated QA.
- Final preview gallery contains 27 source-mode screenshots, including a separate anonymous browser's public chat becoming a waiting run in the already-open Studio history, then updating the selected trace/canvas to completed after the guest answers. The realtime segment records one Studio document load (no reload) and ready/runs_changed frames; subsequent gallery navigations are recorded separately. Includes mobile dialog top/bottom and created-state save disclosure in both themes. Gallery/index.html and ZIP stay outside Git. Owner preview approval is pending.
- Remaining verification is deliberately deferred: automated regressions/security/layer/envelope checks, Redis multi-process delivery/reconnect and access-revocation scenarios, native drag ghost rendering and physical-device keyboard behaviour. No test suite, test edits, typecheck/build/lint, CI, push, merge or release was performed in this implementation/preview turn.

## Handoff Notes

- Owner-approved finish/merge is now in progress on PR #305; the earlier preparation-only restrictions below are historical and superseded for this authorised sequence. Published tags remain immutable, and no release success will be claimed before registry/workflow verification.
- Draft PR: https://github.com/quinguyen1502/superstep/pull/305 into develop. Local canonical full checks and re-review/QA pass; remote checks are tracked on that PR. Keep the same PR for owner feedback and later finish/squash/Ready. No merge/release performed.
- Delivery state: entering review to open the same-task Draft PR after local validation/re-review/QA. Owner review is still required before Ready/done or merge; no release work is included.
- Follow-up implementation checkpoint: 7c7fc06a, on the same task/branch under the owner's “Xử lý đi” instruction. Findings 1–3 resolved; canonical validation 8/8 passed, re-review approved and QA passed with documented manual/environment follow-ups. Earlier failed evidence below is historical, not the current implementation outcome.
- Current-checkpoint focused backend: 56 passed / 1 skipped in 13.23s (service contract, live history, layers, envelope, chat sessions/public runs/socket v1/recovery). Redis 5.0.5 with URL protocol=2: 8 passed / 1 skipped in 4.57s, including a separate Python publisher process reaching the history socket. This is multi-process transport evidence, not Redis 7 acceptance.
- Current-checkpoint selected UI regressions: 22 passed in 1.8m (editor-followups, canvas-menu, alignment, versions, time-travel, template-editor, panel-layout). Explicit state creation, duplicate validation, immediate selection, Undo, keyboard outline, mobile fixed header/footer and slow public run running→completed without Studio navigation all pass. Active history duration is nonnegative. Passed screenshots remain ignored/outside the delivered Git diff.
- The first fix-stage Factory rerun on superseded 181f0071 passed 7/8 commands but backend exceeded its 900s policy timeout. Final-source independent backend and canonical full profile both pass without timeout increase or failed-check suppression; logs /private/tmp/superstep-0256-fix-backend-final.log and /private/tmp/superstep-0256-fix-factory-final.log. Task-local arm64 Node wrapper resolves the earlier Python-spawn architecture mismatch without dependency changes. Source snapshots are chat-only, preserving ordinary editor/ad-hoc storage behaviour.

### Historical validation (before owner-authorised fixes)

- Current implementation checkpoint: ce9c81281c4cb9fa894ca370d0ec5d7c3dadacbd, clean before validation. Owner approval includes the current uncommitted source at that checkpoint, then coverage additions. No source/test fix after validation failures.
- Review: .factory-state/artifacts/REV-0231-task-0256-editor-usability-followups.md (rejected to development).
- QA: .factory-state/artifacts/QA-0231-task-0256-editor-usability-followups.md (fail).
- Independent root build/lint pass; npm tests 157 frontend + 21 React + 102 TypeScript SDK = 280 pass. Targeted 21 UI tests: 19 pass / 2 fail because a new exact-'none' shadow assertion rejects transparent zero-sized Tailwind layers; creation/Undo/dialog checks after it were not reached.
- Full backend: 1188 pass / 65 skip / 3 fail, all new live-history WebSocket close/reconnect CancelledError tests. Focused memory and Redis/RESP2 both reproduce 2 pass / 3 fail. Redis installed locally is 5.0.5; default RESP3 first fails HELLO. URL protocol=2 is an environment-only diagnostic, not Redis 7/multi-process acceptance.
- Canonical Factory full profile completed 3/8 passed, 5 failed. Besides the real backend failures, root build/lint/test and SDK TS test hit x64-native module missing errors. Direct shell Node reports arm64; Python-spawned Node reports x64. Use a task-local explicit-arm64 Node wrapper for a future full rerun; do not add/reinstall project dependencies to work around this transient runner mismatch. SDK Python, TS build/typecheck pass. Actual logs are /private/tmp/superstep-0256-{factory-full,build,lint,units,e2e,memory-history,redis-history-resp2}.log. The tracked verification/latest.yaml now contains the failed run; no stale green report is used.
- Blocking review gap: non-checkpointing public/socket chat plans do not persist/publish their running/progress row. Current preview/E2E proves eventual waiting/completion, not immediate start of a slow run. Next source pass must implement bounded running/progress history without changing recovery semantics, fix/understand cancellation-safe subscription cleanup, correct the nonvisual-shadow test and rerun the rest of its assertions. Keep these on TASK-0256.
- Factory structure and IDs pass, with known installation-receipt/no-todo warnings; diff check passes. Generated Playwright traces/screenshots moved to /private/tmp/superstep-0256-e2e-results (recoverable there), outside Git. Review/QA IDs REV-0231/QA-0231 were allocated after fresh fetch against all refs.
- task-validation/task-review/task-qa require reporting failures without implementing fixes. Stop before Ready/push: task remains doing, no PR opened, no merge/version/tag/release. Owner preview approval is recorded, but does not constitute acceptance of the remaining findings.
