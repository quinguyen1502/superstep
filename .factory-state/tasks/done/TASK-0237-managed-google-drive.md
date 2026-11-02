# Task

## Metadata

- Project: superstep
- Task ID: TASK-0237
- Status: done
- Owner: Thái Quí Nguyễn
- Created/Updated: 2026-11-02
- Requirement IDs: REQ-0085
- Design IDs: DES-0003
- Architecture IDs: DEC-0083

## Objective And Scope

Google Drive managed tools for fixed-folder list/search, metadata, bounded text/Google Doc reads and plain-text file creation. Encrypted service-account/authorised-user credentials, shared Google auth helper preserving Sheets behavior, safe read-only creation reconciliation, schema-driven UI/docs/screenshots. No destructive file tools, recursive/binary transfers, interactive OAuth, live files or deployment.

## Related Artifacts

- `.factory-state/artifacts/REQ-0085-managed-google-drive.md`
- `.factory-state/artifacts/DES-0003-managed-google-drive.md`
- `.factory-state/decisions/DEC-0083-managed-google-drive.md`
- `.factory-state/artifacts/PLAN-0005-managed-google-drive.md`
- `.factory-state/artifacts/REV-0214-task-0237-managed-google-drive.md`
- `.factory-state/artifacts/QA-0214-task-0237-managed-google-drive.md`
- `docs/backend-architecture.md`, `docs/ui-conventions.md`, TASK-0233/0235/0236 and their review/QA records.

## Acceptance Criteria

- Four tools configure/discover/use through MCP/Agent, with encrypted credentials and fixed-folder targets. OAuth refresh and service-account JWT are correctly scoped and use fixed endpoints.
- Direct-child/trashed/shortcut/Shared Drive checks, escaped queries, bounded pages/text, metadata and native Doc export work. My Drive service-account create refuses before upload.
- Lost creation response/crash can reconcile a single matching marker/checksum without another upload; duplicate/missing/incomplete/mismatched results remain unknown. Known results replay and dry runs stay offline.
- Owner/org policy, invalid credentials/IDs, auth/provider failures, response bounds and secret redaction covered. Existing Sheets/HTTP/channel behavior remains compatible.
- en/vi controls/help/docs, both themes screenshots; full checks and advisory review/QA before handoff.

## Validation Plan

- Focused Drive/managed/Sheets/auth/security/layer/envelope tests with fake HTTP; frontend build/lint/unit and browser actual fake-provider calls/screenshots.
- Full Factory profile, en/vi handbook/media, factory validation/IDs/diff, review and QA. No new dependency/migration expected.

## Dependencies And Assumptions

- Stack on TASK-0236/#283 at b3fe373 under PLAN-0005; branch factory/task-0237-managed-google-drive. Owner authorises implementation and tests; merge approval is separate.
- Existing project commands/runtimes from project.md and TASK-0236. Shared Drive creation requires Google permissions/storage; personal users supply authorised refresh credentials.

## Activity Log

- 2026-11-02: Owner explicitly approved merging PRs #278–#284 into develop and requested removal of every evidence screenshot. Existing review/QA passed; this PR carries TASK-0237 to done with human approval and is squashed to one task commit. All evidence images are removed from the branch; historical screenshot paths in review/QA are intentionally retired while textual checks and handbook images remain. Rebase onto latest develop and final-head integration CI gate merge. No release or live provider cutover authorised.

- 2026-11-02: Updated adapter screenshot capture passed four en/vi/light/dark variants (29.1 s). Verified all eight menu items have icons and Sheets/Drive/HTTP retain their icons after selection; four updated menu images in `.factory-state/evidence/task-0237/adapter-logos/`. Temporary capture script removed. No real credentials/provider calls; this follow-up does not claim a new full-profile result.
- 2026-11-02: Owner clarified that Sheets/Drive/HTTP also need recognition icons. Added Google's original Sheets/Drive SVG marks and a theme-coloured HTTP Globe to the shared ChannelLogo; every managed adapter now renders by adapter ID instead of requiring a channel reference. Source URLs and UI brand-colour convention recorded, no dependencies or remote runtime assets. Same task/PR follow-up; updated screenshot capture follows.
- 2026-11-02: Owner requested screenshots for channel logos. Isolated Playwright capture on 8f610d5 passed four en/vi/light/dark variants (17.6 s), checking five channel adapter logos and the selected adapter/channel icons. Twelve images saved in `.factory-state/evidence/task-0237/channel-logos/` (adapter menu, channel menu, selected form). Synthetic channel records only; temporary capture spec removed after use. No application source changes in this capture step.
- 2026-11-02: Owner requested a quick UI follow-up: add logos to channel selection. Existing Human/Chat/Audit selectors already use ChannelLogo; managed adapter options now derive the channel kind from resource_kind and managed channel options reuse ChannelLogo. Radix SelectValue carries the selected item's icon and label. Existing labels/accessibility and theme conventions retained, no new brand assets/dependencies. Scoped-change follow-up on the same task/PR; no local validation or new screenshots run for this follow-up, so prior QA evidence applies to fe56192 only.
- 2026-11-02: Full profile passed all eight checks on fe56192 (backend 466.85 s); source CI passed in 6m19s on Draft #284. Default fixture-off MCP/session browser regression four passed (25.2 s). REV-0214/QA-0214 updated to pass. Verification-only follow-up; task remains review pending human approval, no merge or live Google changes.
- 2026-11-02: Final Drive browser four variants passed (40.7 s), including actual lost-acknowledgement/read-only UI recovery without repeat upload. Committed fe56192 and opened Draft #284 on #283; full local verification and source CI in progress. Parent #283 head b3fe373 and independent #281 head 0a4bb9d both have green Factory CI.
- 2026-11-02: Implemented four Drive tools, shared auth/redaction and UTF-8 bounds, encrypted settings/locales, fake-provider/backend/browser tests and bilingual handbook. Focused regression 120 passed; frontend build/lint/149 unit passed; combined browser 12 passed. Enter review for one Draft PR; REV-0214/QA-0214 record advisory review and pending full profile/source CI. No merge/live account changes.
- 2026-11-02: factory ready exited 0 before source edits. Move to doing for owner-authorised implementation/tests on the dedicated branch.
- 2026-11-02: Owner request accepted; allocated all artifact IDs after fetch/all-ref scan. Clean dedicated branch from b3fe373. Read context and official Google auth/storage/upload/property contracts. No implementation source edits before factory ready.
