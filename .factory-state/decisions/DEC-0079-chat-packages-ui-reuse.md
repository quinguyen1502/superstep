# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0079
- Status: Accepted on 2026-10-31. The owner approved PR #271 with all 11 recommendations of PLAN-0002 ("Duyệt plan #271 theo đề xuất cả 11 câu, merge và bắt đầu code giai đoạn 1").
- Owner: Thái Quí Nguyễn
- Created: 2026-10-31
- Updated: 2026-10-31
- Related Requirements: REQ-0082
- Related Tasks: TASK-0220, TASK-0222, TASK-0223, TASK-0224, TASK-0225, TASK-0226, TASK-0227
- Related Architecture: DEC-0008 (UI conventions, shadcn), DEC-0078, DEC-0080

## Context

- `sdk/typescript` is a standalone npm package `@superstep/sdk` 0.1.0 with no runtime dependencies, published by `sdk-publish.yml` on `sdk-ts-v*` tags (environment `npm`).
- The chat UI is in `frontend/src/components/chat/*` (`chat-panel`, `chat-thread`, `chat-composer`, `chat-attachments`, `chat-rating`, `chat-steps`, `chat-confirmation`, `chat-markdown`, `chat-logo`, `use-chat-run.ts`) built on shadcn components and theme tokens; the widget is `frontend/src/widget/widget.ts`, built with the frontend.
- The frontend is a single Vite app (`frontend/package.json`, name `frontend`); there is no workspace setup.

## Options

### Headless chat client

- **A. Inside `@superstep/sdk` under `client.chat`** (recommended): one install, one auth story, zero dependencies; tree-shakable entry `@superstep/sdk/chat`.
- **B. A separate `@superstep/chat` package**: cleaner split, but two versions to keep in step and a second publish job.

### UI toolkit and reuse

- **A. Extract into `packages/react` (`@superstep/react`) in an npm workspace that the studio frontend consumes** (recommended): one source of truth; the studio is the first user and its e2e and screenshots guard the package. Components keep shadcn markup but read theme CSS variables (`--ss-*` mapped to the shadcn tokens) so a host app can theme them without Tailwind.
- **B. Copy the components into a new package**: fast now, but two chat UIs drift (violates DRY).
- **C. shadcn registry only** (host apps copy components with the shadcn CLI): good for Tailwind users, useless for others, and no hook updates. Offered later as an extra on top of A.

### Styling

- Ship a prebuilt CSS file (`@superstep/react/styles.css`) compiled from Tailwind with a `ss-` prefix and scoped under `.superstep-chat`, so it never leaks into or depends on the host's Tailwind. Theme through CSS variables and a `theme` prop (`primary`, `radius`, `font`, `colorScheme`).

### Package names and publishing

- `@superstep/sdk` (headless, TypeScript), `@superstep/react` (web UI), `@superstep/react-native` (DEC-0080), Python `superstep` (headless).
- Tags in `sdk-publish.yml`: keep `sdk-ts-v*` and `sdk-py-v*`; add `sdk-react-v*` and `sdk-rn-v*`, each publishing with npm provenance from the `npm` environment and checking that the tag equals the package version.
- Versions: `@superstep/sdk` 0.2.0 adds chat (minor, additive); the UI packages start at 0.1.0; peer dependency on `@superstep/sdk` `^0.2.0` and React `>=18`.

## Decision (recommended)

1. Headless chat in `@superstep/sdk` (option A), with a transport interface (`WebSocketLike`) so browsers, Node (global or `ws`) and React Native share code.
2. `useChat` lives in a small framework-agnostic store (`createChatStore` in `@superstep/sdk/chat`) plus thin React bindings, so `@superstep/react` and `@superstep/react-native` share state logic (DEC-0080).
3. npm workspaces at the repository root: `frontend`, `packages/react`, `packages/react-native`, `sdk/typescript`. The frontend imports `@superstep/react` from the workspace; the studio-only parts (settings dialog, attachment settings, side panel) stay in `frontend`.
4. The widget stays built by the frontend, gains the JS API, and loads the same `/c/{slug}?embed=1` page in its iframe (no React in the host page).
5. Publishing as above; README and handbook pages per package.

## Rationale

- One UI codebase guarded by the studio's existing e2e keeps quality high and avoids drift; the headless store shared by web and native avoids a third copy of the state logic.

## Risks

- The extraction touches a working UI: mitigated by a no-visual-change rule (screenshot comparison) and a dedicated task (TASK-0223) before new features.
- A workspace change affects CI caching and Docker builds of the frontend: TASK-0223 updates `ci.yml` and `frontend` Dockerfile steps.

## Open Questions

1. Headless chat inside `@superstep/sdk` or a separate `@superstep/chat`? Recommendation: inside, with a `/chat` subpath export.
2. Also publish a shadcn registry for Tailwind users? Recommendation: later.
3. Is moving to npm workspaces acceptable for the repository? Recommendation: yes (no new tool; npm 7+ supports it).

## Approval

- Approved By: pending
- Approved On: pending

## Review Or Revisit Trigger

- If the extraction slows the studio or the bundle grows by more than 10 percent.
