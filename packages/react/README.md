# @superstep/react

Shared React chat presentation extracted from Superstep Studio. This package is under development in PLAN-0002; the public `useChat`, composed Chat and scoped theme stylesheet follow in TASK-0224. No package is published by this extraction.

The Studio and public chat page use the same `ChatThread`, `ChatComposer`, attachment components (`AttachmentChip`, `TurnFiles`), `ChatRatingBar`, `ChatSteps`, `ChatConfirmation`, `ChatMarkdown`, and `ChatLogo`. Components keep the existing shadcn markup and theme tokens. The workspace frontend supplies its existing Tailwind stylesheet and en/vi i18next resources.

`ChatPresentationProvider` optionally supplies host capabilities for child-step content and reviewer navigation. No Studio router, API client, credential, settings dialog or run repository is imported here. The Studio adapter stays in `frontend/src/components/chat/chat-thread.tsx`.

From the repository root:

```sh
npm ci
npm run build
npm run lint
npm test
npm run test:e2e
```

The root lockfile owns all three npm workspaces (`frontend`, `packages/react`, `sdk/typescript`). Development resolves package source through the `source` export condition; normal ESM consumers receive the built `dist` entry and declarations. `./ui/*` and the helper subpaths serve the workspace extraction and may change before the first public toolkit release. React, React DOM, i18next and react-i18next are host peers; keep one instance of each.

Real browser and four-variant screenshot checks guard the extraction. Screenshots remain temporary files / CI artifacts, never package files or Git evidence. Python's shared version and all release tags are unaffected.
