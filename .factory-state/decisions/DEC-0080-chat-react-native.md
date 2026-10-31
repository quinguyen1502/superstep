# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0080
- Status: Accepted on 2026-10-31. The owner approved PR #271 with all 11 recommendations of PLAN-0002 ("Duyệt plan #271 theo đề xuất cả 11 câu, merge và bắt đầu code giai đoạn 1").
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Related Requirements: REQ-0082
- Related Tasks: TASK-0227, TASK-0228
- Related Architecture: DEC-0077, DEC-0079

## Context

- Owner decision: React Native first; native iOS and Android through a WebView of `/c/{slug}` with a guide and a token bridge; no Swift or Kotlin SDK now.
- React Native has global `fetch` and `WebSocket`, but no DOM: shadcn components (Radix, Tailwind CSS) do not render there.
- File upload in React Native uses `FormData` with `{uri, name, type}` objects instead of `Blob`.

## Options

### React Native package

- **A. A separate `@superstep/react-native`** (recommended): native components (`Chat`, `MessageList`, `Composer`, `QuestionCard`) built on React Native primitives only, sharing `createChatStore` and `useChat` logic from the SDK; no `react-dom` in the dependency tree.
- **B. RN support inside `@superstep/react`** (platform files `.native.tsx`): one package, but web users pull RN typings, and Metro and web bundlers resolve platform files differently; fragile.
- **C. React Native WebView of `/c/{slug}` only**: no native feel, but zero UI work. Kept as the fallback in the guide.

### Markdown in RN

- Render a small safe subset (paragraphs, bold, italic, code, links, lists) with a built-in renderer; allow a `renderMarkdown` prop to plug in a library. No heavy dependency.

### Native WebView token bridge

- The `/c/{slug}?embed=1` page listens for `window.Superstep.identify(token)` (the same API as the widget, TASK-0225) and a `superstep:token-request` message to the host:
  - iOS: `WKWebView` with a `WKScriptMessageHandler` named `superstep`; the host answers with `evaluateJavaScript("Superstep.identify(...)")`;
  - Android: `addJavascriptInterface` is avoided (security); use `WebViewCompat.addWebMessageListener` with the allowed origin of the studio, or `postWebMessage`;
  - React Native WebView: `onMessage` and `injectJavaScript`.
- Origin checks: the page only accepts identify calls from the native bridge (not from other frames); the native side only answers when the WebView's current origin is the studio.

## Decision (recommended)

1. Option A: `@superstep/react-native` 0.1.0, peer `react-native >=0.73`, `@superstep/sdk ^0.2.0`; optional peer `expo-document-picker` or a host-provided `pickFile` prop for attachments.
2. Shared logic: `useChat` is the same hook implementation (from a React-only shared module in `@superstep/sdk/react` subpath or duplicated as a thin binding of `createChatStore`; recommendation: a thin binding per package, about 50 lines, to keep the SDK free of React).
3. An Expo example app in `examples/react-native` with Jest and React Native Testing Library tests in CI; no device e2e in CI (manual checklist with screenshots on iOS simulator and Android emulator in the task).
4. The native WebView guide (en, vi) with Swift and Kotlin snippets and the bridge protocol; browser e2e covers the page side of the bridge.

## Open Questions

1. Separate RN package or platform files in `@superstep/react`? Recommendation: separate package.
2. Device e2e (Detox or Maestro) in CI? Recommendation: not now; unit tests plus a manual screenshot checklist.

## Approval

- Approved By: pending
- Approved On: pending

## Review Or Revisit Trigger

- Demand for native Swift or Kotlin SDKs, or RN New Architecture changes that break the components.
