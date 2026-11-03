# Review

- Project: superstep
- Review ID: REV-0217
- Task ID: TASK-0222
- Created/Updated: 2026-11-02
- Reviewer: Codex self-review; advisory, owner accepted 2026-11-02
- Outcome: approved for QA
- References: REQ-0082, PLAN-0002, DEC-0077–0080, DEC-0008, TASK-0222, QA-0217

## Scope And Findings

Own diff above TASK-0221/#286 at bc1cd9f: local Node host, headless-store browser page, shared fixture/build/acceptance scripts and CI, en/vi guide/release notes, ignored artifacts and a browser transport correction. No backend schema, production route, account system or React UI package is introduced. No unresolved blocking implementation findings.

Resolved by actual browser testing: default platform fetch was called with the SDK object as receiver and Chrome rejected its Web IDL invocation. Both SDK constructors now bind the selected fetch implementation to globalThis, including explicit native-fetch overrides; the shared contract runs that regression in Node/jsdom/native-like contexts (94 SDK tests total), and Chrome acceptance proves the real transport. Earlier injected mocks alone did not detect this browser behavior.

Resolved UI issues: explicitly generate imported shadcn classes, avoid native file-input English text in the Vietnamese page, prevent hidden file-control mobile overflow, use the selected language for request locale, and keep root bootstrap separate from the component module. Sample oxlint and strict UI class checks pass without warnings. Theme/locale desktop screenshots and a 390px mobile no-overflow check pass.

## Auth And Data Review

The server is loopback-only and requires CHAT_HOST_DEMO=1. Two fixed personas are a documented sign-in stub; submitted user IDs cannot select signed claims. Opaque HttpOnly/SameSite=Lax cookies reference bounded server-owned sessions, logout invalidates them, token responses are no-store, and the secret stays in Node. Exact Host/Origin admission, central envelope errors, CSP/static path bounds and no secret echo are tested. The browser uses shared api/errorText and shadcn controls, theme tokens, labelled fields, feedback status/log regions and identical en/vi keys. There is no resource-delete UI.

The studio is on 127.0.0.1 and the host on localhost, with explicit app-key origins. HTTP omits cookies, sockets use auth frames without query tokens, and actual two-customer sessions remain isolated. A second host proves HTTP/socket origin refusal. A spare origin-admitting key makes revocation errors readable over CORS; the revoked signing key cannot create another turn. Bundle inspection finds no ephemeral app secret or owner token. Network auth traces are disabled; screenshots show only synthetic UI data.

Fixture scripts pin temporary SQLite, DB attachment storage, empty model credentials and fresh test keys. Occupied ports refuse before seeding; Node security tests obtain an ephemeral port and wait for their own process. No existing service, real provider or production resource is used. Python's shared version is preserved per owner amendment; no release tags are created.

## Validation And Decision

Final full Factory profile on 80116c2: 8/8 passed (backend 480.53 s). Final fixture guards were verified by the full cross-origin acceptance and SDK integration scripts: Node 3 passed, Playwright scenario passed, Python live 8 and TypeScript live 7 passed. SDK 94 unit cases/typecheck/generated contracts, sample build/lint/UI review and both handbook/media checks passed. Final CI acceptance is the task PR's Chat host e2e check, recorded in its checks/description. Human review/merge and publication remain separate.

## Owner Approval And Finalisation

Owner accepted the reviewed phase-2 stack on 2026-11-02 ("Duyệt"). This task moves to done on existing #287, restacked onto finalised #286 and squashed for Ready delivery after final gates. The reviewed fetch binding change and shared regression have moved to #285; no final stack source behaviour changes. Original head ae16a7c passed the host gate and all 19 successful checks (one deployment skip), with screenshots at https://github.com/quinguyen1502/superstep/actions/runs/41434119564/artifacts/13134549352. Rewritten-head CI must pass and its fresh screenshot artifact must be linked before Ready. Earlier review/pending entries are historical. Merge and publication remain unapproved; no images are committed.
