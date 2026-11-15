# Review

## Metadata

- Project: superstep
- Review ID: REV-0245
- Task ID: TASK-0228
- Reviewer: Grok (advisory; owner authorised implementation and green merge: "Do 0228 in parallel")
- Created: 2026-11-07
- Updated: 2026-11-07
- Outcome: approved for QA

## Review Scope

Branch `factory/task-0228-native-webview-bridge-guide`: `frontend/src/widget/frame-bridge.ts`, `frontend/src/widget/api.test.ts`, `frontend/e2e/chat-native-bridge.spec.ts`, `handbook/docs/{en,vi}/run/chat-native-webview.md`, `handbook/docs/{en,vi}/run/chat-widget.md`, `handbook/mkdocs.yml`, `handbook/mkdocs.vi.yml`, task artifacts.

## Reference Artifacts

REQ-0082, PLAN-0002, DEC-0080, TASK-0225 (widget bridge).

## Findings

### Blocking

- None.

### Non-Blocking

- DEC-0080 sketched a `superstep:token-request` message; the implementation reuses the existing `superstep-chat:` names of the TASK-0225 protocol (`superstep-chat:ready`, `superstep-chat:token-request`) so one prefix covers web and native. Documented in the guide and the task log.
- The native channel is detected from objects only the app can add (WKScriptMessageHandler, WebMessageListener with an origin allowlist, react-native-webview). Origin and main-frame checks are the app's job and are shown in every snippet; the page side only uses the channel as the top-level document.
- A late `identify` (after the 10 s timeout) is treated as an identity switch and reloads history; acceptable and documented ("within 10 seconds").
- Swift, Kotlin and React Native snippets are not compiled or run on a device in CI (DEC-0080: no device e2e); stated in the guide.

## Standards And Architecture Alignment

No backend, API, schema, error-code or dependency change. The frame (widget) path is unchanged and its unit and e2e tests still pass. Tokens are never written to the URL, storage or messages to the app; en/vi pages in parity.

## Design Alignment

DEC-0080 decision 4: native WebView guide (en, vi) with Swift and Kotlin snippets and the bridge protocol; browser e2e covers the page side.

## Review Decision

Approved for QA.
