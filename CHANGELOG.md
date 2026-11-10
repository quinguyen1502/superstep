# Changelog

All notable changes to Superstep. Versions follow [Semantic Versioning](https://semver.org/); dates are in UTC+7.

## Unreleased

### Added

- **Public schedule API.** A workflow token can list, create, update, delete and preview cron schedules of its own workflow (`/api/hooks/workflows/{wid}/schedules`). The Python and TypeScript clients gain the matching methods. Package versions are unchanged. A schedule still runs as the token's owner, and it fires only while a worker is running.
- **Readiness endpoint.** `GET /api/ready` checks the database and, when `REDIS_URL` is set, Redis, and answers 503 `SERVICE_NOT_READY` when either fails. It also reports queue depth, the oldest queued run and worker heartbeats. `GET /api/health` stays a liveness check and is unchanged; deploy templates keep using it.
- **More OpenTelemetry metrics.** With `STUDIO_OTEL_METRICS=1`, the backend also exports HTTP requests and latency by route template, open WebSockets, model tokens, cost, unpriced calls, errors and fallbacks by model and provider, reaped and recovered jobs, and gauges for the database and Redis probes, queue depth, worker slots and heartbeat, the in-memory bus and process CPU and memory. Labels never carry a user id, run id or raw path. Run metrics gain `workflow_id`.
- **Settings → Usage.** Admins with `users.manage` see runs, success rate, tokens and estimated cost for the last 24 hours, 7 days or 30 days, runs over time by status, the top workflows by runs or cost, and the share of runs without a model price. A product health block counts waiting and expired approvals, failed and retrying webhook deliveries, and overdue or stopped schedules. The same data is at `GET /api/admin/usage` and `GET /api/admin/usage/health`. Set `STUDIO_GRAFANA_URL` to add a Grafana link. With `STUDIO_OTEL_METRICS=1`, the worker also exports these product health counts as gauges. A migration adds indexes on run start time, approval waits and webhook deliveries.

### Changed

- A provider HTTP 429 now fails with `PROVIDER_RATE_LIMITED` instead of `PROVIDER_BAD_RESPONSE`. It still answers 502 to API clients and still switches to a configured fallback model.

### Fixed

- Schedules accept every IANA time zone a browser reports, such as `Asia/Saigon`, on images without system zone data: the backend now depends on `tzdata`.

## 0.12.0 (2026-11-07)

### Added

- **Browser tools.** A managed browser connection with an origin whitelist, a local Docker Playwright worker or a self-hosted Browserless controller, login profiles, sessions that continue across chat turns, approval before a mutating action, dynamic URLs, typed recipes, Settings, and a filtered trace. Public chat shows only allowlisted browser facts. English and Vietnamese handbook pages include screenshots. Python and TypeScript exports can run the browser tools, including one live page. The connection stays off until `STUDIO_ENABLE_BROWSER=1`. The local runtime also needs `STUDIO_ENABLE_BROWSER_RUNTIME=1`.
- **Code export closer to a running workflow.** HTTP calls pin the checked address. Model fallback can carry attachments. MCP uses Streamable HTTP, Retriever calls the knowledge-base API, and Send email uses SMTP. A model credential can use its own `LLM_CRED_<n>` slot. A human approval can post a channel notice, wait for a deadline, and apply AI review. A managed connection reads `MANAGED_<n>_SETTINGS` and `MANAGED_<n>_SECRETS`. Credential ids, channel targets, judge instructions and connection secrets are not written into the file. A step with no adapter still raises a placeholder.
- **Local studio access.** The handbook explains how to open a local studio through a tunnel, and Settings → Channels links to the matching guide.
- **WebView token bridge.** A host page can pass a chat token into an iOS, Android or React Native WebView. The handbook has the snippets. This is not a published React Native package.

### Changed

- An exported service stub fails immediately when `LLM_PROVIDER` is set and its required variable is missing. An offline run still announces a mock.

### Upgrade

- Shared server, Python SDK, CLI, frontend and installer: **0.12.0**. React toolkit: **0.1.3**. TypeScript SDK stays **0.2.0**.
- Apply migrations `0055_browser_artifacts`, `0056_browser_sessions`, `0057_browser_conv_sessions` and `0058_browser_approvals` before serving traffic. They add browser artifact, session, conversation and approval records. Back up the database first. No new required Python or npm dependency.
- Browser stays disabled until the flags above are set. The React Native package and cross-language code nodes are not in this release. No live provider or bot cutover is included.

## 0.11.2 (2026-11-05)

### Fixed

- Palette drag previews are clipped to the rounded card; time-travel columns align and preserve an accessible State label. Empty dropdowns visibly explain missing options, with distinct loading/error feedback for existing lookup flows.
- Shared alerts and small controls align icons/text; Restore has balanced spacing. Attached panel tabs have no box shadow and retain a keyboard focus outline.
- Long dialogs keep headers and actions visible while only the body scrolls, including Chat settings on small screens.
- Chat runs from Studio, public pages and other tabs appear in the workflow run log while still running, then update progress/status without an application reload. Active-run durations no longer become negative.
- Run-history observers close/reconnect cleanly and recheck existing workflow/run permissions. Invalidation messages contain no run contents; bounded chat-only snapshots do not enable queued-job replay.

### Improved

- General shows the existing node description and incoming/outgoing connections.
- State pickers offer explicit named/typed creation with duplicate validation, immediate selection and Undo. Saved chat settings disclose when the workflow draft must also be saved.

### Upgrade

- Shared server/Python SDK/CLI/frontend version: **0.11.2**. React toolkit: **0.1.2**. TypeScript SDK stays **0.2.0**. No database migration or new dependency; back up normal application data before upgrading.
- Running socket snapshots are display state, not a new durable replay guarantee. Existing queued-run recovery is unchanged. The native React Native toolkit and WebView bridge, physical-device keyboard/native drag-ghost QA and live provider/bot cutovers are not included.

## 0.11.1 (2026-11-05)

### Fixed

- Chat feedback controls stay on one row on narrow screens; comment inputs retain their complete focus ring. New chat sits before Expand and Close has a consistent visual size.
- Workflow chat history, visitor dislike filtering and 7/30-day feedback totals move to **Chat history & feedback** in the workflow menu, keeping the Chat panel focused on conversations. Existing session visibility rules remain unchanged.
- Node palette/State schema and General/Settings/Data/Execution use attached panel tabs. Trace errors, empty output, State diff and version comparisons have clearer layouts and messages.
- New Google Sheets connections leave sheet name and data-column count empty. Existing settings are preserved. Channel cards initially expand only connected services; schedule time zones are selectable.
- Public-page settings collapse from a plain heading with a chevron. Attachment configuration explains invalid state fields and prevents invalid saves. Sharing labels, notifications and exact-name deletion dialogs render consistently on narrow screens and in dark mode.
- Public chat session-operation errors stay inline instead of incorrectly replacing an already loaded page with “Chat not available”; publication checks remain enforced. The separately reported deployment-specific first-message rejection still needs its URL/environment to diagnose.

### Changed

- Python/TypeScript workflow exports retain managed steps as explicit TODO placeholders that fail until implemented, including Agent tools and child workflows. Connection settings and credentials are excluded; unrelated generated code remains available.
- Backend distributions now include the chat socket JSON schemas required when starting an installed wheel.
- Shared server/Python SDK/CLI/frontend version: **0.11.1**. React toolkit: **0.1.1**. TypeScript SDK remains **0.2.0**. No database migration is introduced.

## 0.11.0 (2026-11-03)

### Added

- **Public Chat API v1 and third-party identity**. Versioned HTTP and typed WebSocket APIs,
  generated OpenAPI/AsyncAPI contracts, history recovery, files and ratings. Per-chat app keys let an application's
  backend mint short-lived user tokens; secrets stay on the server and conversations remain scoped to each user.
  Legacy routes remain aliases. API contract versioning is independent of the application version.
- **Headless chat SDKs**. TypeScript 0.2.0 and Python 0.11.0 support streaming, sessions/history,
  Human text/form answers, files, feedback and server-side signing helpers. Token refresh is bounded; interrupted
  execution recovers saved history instead of replaying writes. Python SDK, CLI and server share version 0.11.0.
- **Shared React toolkit and programmable widget**. `@superstep/react` 0.1.0 provides `useChat`,
  composable chat controls, isolated themes/locales and the same presentation used by Studio. `window.Superstep`
  supports identity, lifecycle and events. English/Vietnamese guides and a shared headless/React/widget sample
  host cover origins, token refresh, Human answers, files and feedback; CI exercises React 18/19 consumers.
- **Edit and regenerate chat messages**. Editing a saved root message or regenerating the
  latest terminal answer opens an independent conversation branch. Original history/feedback stays intact and
  files are copied independently. Studio, public chat, widget and TypeScript/Python/React helpers share durable
  admission and recovery. Confirmation explains that the current workflow runs again and API calls, writes or
  notifications may repeat; Human/reviewer approvals are requested again. Inherited turns remain read-only.
- **Generic managed tools**. Existing MCP nodes and Agent tool slots can use configured HTTP
  API operations, Telegram, Google Sheets/Drive and existing Slack, WhatsApp, email and Teams channels with fixed
  destinations, encrypted authentication, shared permissions and bounded schemas. Unknown write outcomes stay
  blocked for read-only reconciliation instead of automatically repeating non-idempotent actions. Google Drive
  supports folder-scoped search/read and plain-text creation; Google authentication is shared with Sheets.
- **Explicit event bindings**. Telegram messages and signed JSON webhooks use sender admission, typed
  state mapping and atomic delivery deduplication through existing trigger controls.
- **LLM model fallback**. An LLM node may use one alternate credential/model after a provider failure.
  Credential permissions are checked first, failed-primary tokens are not published as an answer and attempts
  appear in the trace. Mock runs remain offline; unsupported code exports fail explicitly.
- **Telegram expense workflow example**. A portable sample template combines event admission, model
  fallback and managed tools with strict expense validation, separate expense/submission dates and a success
  reply gated on a confirmed Sheets write. Bilingual setup guidance and duplicate/replay/reconciliation tests
  accompany the example; it is not a built-in expense-management module.

### Fixed

- **Chat Agent input duplication**. An Agent using the chat history and the new message in its prompt
  sends the message to the model once, in Studio and generated Python/TypeScript workflows.
- **Concurrent token names**. Active PAT names are unique per user. Losing creates return
  `PAT_NAME_TAKEN`, CLI sign-in chooses the next free name and existing duplicates are renamed during migration.
- **Run timeout starts at execution**. Queue/setup and the first progress-checkpoint write no longer
  consume the run's execution timeout; the configured limit itself is unchanged.
- **Revision recovery after newer messages**. SDKs still find an admitted operation's reserved run
  after its branch has continued, without resending execution. The TypeScript store preserves a later Human wait.

### Upgrade

- Back up the database and attachment storage before upgrading. Startup applies Alembic migrations 0050–0054
  from the v0.10.2 schema; existing conversations/files remain readable. Conversation branches use extra storage.
- Use matching 0.11.0 Python SDK/CLI/server versions. TypeScript SDK 0.2.0 and React 0.1.0 retain independent
  package versions. The React Native toolkit and WebView bridge remain deferred; no native delivery is claimed.

## 0.10.2 (2026-10-31)

### Security

- **Request bodies are bounded outside the upload routes again**. Since the upload change below ("Uploads above 10 MB reach the API") the bundled nginx let
  every `/api/` request carry up to 110 MB, including the unauthenticated chat and approval callbacks that read the whole
  body. nginx is back to 10 MB, with `WEB_MAX_BODY_SIZE` only on the upload routes (chat attachments, workflow import,
  knowledge documents), and the app enforces its own ceilings without a proxy too: 1 MB for the callbacks,
  `STUDIO_MAX_BODY_MB` (default 10) elsewhere.
- **An approved CLI sign-in that is never collected leaves no token behind**. The token is now created when
  the CLI collects it instead of being stored in plain text at approval; a token stored by an older version is revoked
  and cleared once its sign-in expires.
- **The CLI sign-in asks for the code from the terminal**. The `superstep login` link no longer
  carries the code, and `/cli/authorize` asks the person to type the code their terminal shows, with a warning, so a
  link someone else sends cannot be approved with one click. Sign-in starts are limited to 10 per client IP per 10
  minutes (`RATE_LIMITED`), and old sign-ins are removed.
- **The CLI sends its saved token only to the server that issued it**. A `--url` or `SUPERSTEP_URL` naming
  another server gets no token; log in there or set `SUPERSTEP_TOKEN`.
- **AI review sends a request it cannot see in full to people**. The judge saw only the first 12,000
  characters, so a field after a long one (a `bcc` after a long body) could be approved unseen; such a request now goes
  to people (cause `too_long`).
- **The attachment orphan sweep only deletes its own files**. It used to delete any file older than an hour
  in the attachment folder or bucket prefix that no row named, including another install's files or the studio's own
  data when the folder was set to the data folder. It now deletes only names of the form `<workflow>/<chat>/<file id>`
  at the configured location. A folder that is or contains the data folder is refused (`/api/health` shows
  `attachment_storage_ok: false`), and an empty S3 prefix logs a warning.

### Fixed

- **The chat remembers a Human node's question with its answer**. The conversation field had the answer
  (`approved`) without the question it answered, and each answer shifted the "Messages remembered" cut by one
  message. The question now comes before its answer and the cut keeps whole exchanges. A form answer (an object) is
  saved as the person's turn too, one `field: value` line per field, so the question is no longer left as the last turn.
- **An answer to a Human node stays in the chat**. Approving, rejecting or typing an answer in the Chat
  panel or on a public chat page showed the answer only until the reply arrived; it was never saved, so it vanished
  and the question above it still looked open. The answer is now saved as the person's turn (and the next turns
  remember it), and the chat keeps the message box busy until the saved reply is read back, so a message sent in
  that moment is no longer taken as a second answer to the finished run or dropped.
- **Three end-to-end tests no longer fail at random**: the delivery log test stopped refreshing after its
  first empty read, the read-only profile test counted the language the normal account saves after sign-up, and the
  chat test typed its next message while the previous reply was still being read. The language sent after sign-in is
  also sent once instead of twice.

- **A body without a length that passes the ceiling answers 413**. On routes that parse JSON, a form or a
  file, a chunked body past the ceiling answered 400 `BAD_REQUEST`; it now answers 413 `PAYLOAD_TOO_LARGE` like a body
  that declares its length.
- **A CLI sign-in is not lost when its token name is taken meanwhile**. If a token with the
  approved name was created before the CLI collected its token, the poll failed with `PAT_NAME_TAKEN` and the sign-in
  was consumed; the new token now gets a free name such as `laptop (2)`.
- **Old S3 attachments stay readable after the s3 settings are removed**. A file's recorded bucket and
  prefix are enough to read it once storage moved to another backend; missing credentials are named in the error.
- **A chat no longer skips the nodes between Start and the first agent**. After a hand-off, the
  next message jumped from Start straight to the agent that answered last, so a masking, filter or lookup step before
  the first agent did not run. The chat now continues with that agent only when Start leads straight to agents;
  otherwise every message runs from Start. The Python, LangGraph and TypeScript exports do the same.
- **A personal access token's last use is written at most every 5 minutes** instead of on every request.
- **An AI review lost to a restart goes to people**. The maintenance sweep sends a step whose review never
  finished to people (cause `restart`): the run owner is told in auto mode and the channel request is sent.
- **The AI review daily cap holds for parallel steps**. Each automatic answer reserves its slot atomically,
  so the steps of one wave cannot pass the cap together; an escalated review gives its slot back.
- **AI review usage is no longer lost on SQLite**. A waiting run's update kept an `approval_review` event
  appended at the same time.
- **Attachments survive a change of folder, bucket or prefix**. Each file records where it was written
  (migration `0048`, filled for older files at start-up), so it is still read from there, and `superstep attachments
  migrate --to fs|s3` moves files between two locations of the same backend.
- **A visitor's upload no longer blocks the server while it is stored**.
- **Uploads above 10 MB reach the API behind the bundled nginx**. The `web` image allows `WEB_MAX_BODY_SIZE`
  (default `110m`) and answers a larger body with the API's `PAYLOAD_TOO_LARGE` envelope instead of an HTML page.

## 0.10.1 (2026-10-31)

### Added

- **Choosing attachment storage at install**. `superstep install` and `deploy` ask
  where chat attachments are stored (`db`, `fs`, and `s3` for the full stack), or take `--attachment-storage` and
  `--s3-*` flags with `--yes`. The S3 secret is read from stdin, `SUPERSTEP_S3_SECRET_ACCESS_KEY` or a hidden prompt,
  never from a flag, and is written only to `.env` (mode 600). `superstep doctor` shows the backend and whether it
  works. The Render demo stays on `db`.
- **Moving and backing up chat attachments**. `superstep attachments migrate --to
  db|fs|s3 [--dry-run] [--batch N]` (and `POST /api/admin/attachments/migrate` for admins) moves files between backends,
  checking size and SHA-256 before switching each file; an interrupted run is safe to start again. Backups include files
  on a folder, and files in a bucket with `--include-attachments`; the manifest records the backend (and bucket and
  prefix). `restore` refuses an archive of another backend unless `--force`. New error codes
  `ATTACHMENT_MIGRATE_TARGET` and `ATTACHMENT_MIGRATE_BATCH`.
- **Attachment storage on S3-compatible services**. `STUDIO_ATTACHMENT_STORAGE=s3`
  keeps chat attachment bytes in a bucket (AWS S3, Cloudflare R2, Backblaze B2, MinIO), set with
  `STUDIO_ATTACHMENT_S3_*`. Downloads still stream through the studio; the bucket is never shown to the browser. Access
  keys are never logged; `/api/health` only says whether the bucket works. `boto3` is the optional `s3` extra and the
  published images include it. CI runs the storage contract against MinIO.
- **Attachment storage on a folder**. `STUDIO_ATTACHMENT_STORAGE=fs` keeps chat
  attachment bytes as files under `STUDIO_ATTACHMENT_FS_PATH` (default `/data/attachments`), written atomically, with
  keys that cannot leave the folder. `/api/health` reports a missing or read-only folder, and
  `attachment_storage_worker_seen` shows whether the worker shares the folder with the API. In docker compose, `api`
  and `worker` share the `/data` volume.
- **Attachment storage port**. Chat attachment bytes go through a storage port.
  `STUDIO_ATTACHMENT_STORAGE` (default `db`) picks where new files go; each file records where its bytes are
  (`storage`, `key`), so files stay readable after a change of backend. The object is written before the row and
  removed after it, the retention loop removes objects without a row once they are an hour old, and downloads stream through the backend with the same
  headers. `/api/health` reports the backend and whether a write, read and delete there works. New error
  `CHAT_ATTACHMENT_STORAGE` (503).
- **Plan: external storage for chat attachments** (Accepted 2026-10-31). Planning records only: a storage
  port with database (default), folder and S3-compatible backends, a migrate command and backup coverage, planned as
  five follow-up tasks. Nothing is implemented yet.

### Fixed

- **AI review counts in usage**. The judge's tokens and cost are added to the run
  it reviewed, through the same usage records as node model calls: run history, the trace summary, the Human node's
  row (tooltip line "AI review"), run metrics in the API and telemetry. A run still waiting for people shows them at
  once. The run's events carry an `approval_review` entry with the usage.
- **Scheduled backups name the S3 bucket**. With `STUDIO_ATTACHMENT_STORAGE=s3`, the archive
  that `backup.sh` writes on a schedule records `attachment_s3` (bucket and prefix) in its manifest, as a manual
  backup does, so `restore` reminds you which bucket to restore separately.
- **Two timing-sensitive tests**. The parallel tool-call test proves the three calls run at once with a
  barrier instead of comparing start and end times. The studio e2e test checks the opened workflow's visible Last run
  badge instead of the first `ok` on the page, which is the phone-only copy hidden on desktop.

### Changed

- **README and handbook home catch up**. The README now covers the `superstep`/`sstep` CLI install and
  commands, chat attachments and their `db`/`fs`/`s3` storage with `superstep attachments migrate`, Agent hand-offs and
  the Help desk template, and AI review of approvals; it also fixes the Code node languages and the docs table. The
  handbook home pages (en, vi) link the Agent, hand-off, chat, AI review and CLI pages. A trigger rate-limit test no longer
  fails when its requests straddle a fixed window's boundary.
- **End-to-end tests in CI**. A new `E2E (Playwright)` job runs the whole Playwright suite, English and
  Vietnamese, on every pull request to `develop`, in three shards with a 30-minute timeout, cached Chromium and Code-mode
  specs on the subprocess runtime. There are no retries; on failure the traces and screenshots are uploaded as
  `e2e-shard-N` (7 days).
- **S3 multipart uploads**. The `s3` attachment backend uploads a file larger than
  `STUDIO_ATTACHMENT_S3_MULTIPART_MB` (default 8) in parts, holding at most two parts in memory, and aborts the upload on
  any failure so the bucket keeps no incomplete parts. Uploads are read in 1 MB pieces into a spooled temporary file,
  refused as soon as they pass the size ceiling (the content-length check still runs first), and stream to the `fs` and
  `s3` backends and from an archive restore. Tested against MinIO, including the abort path.

## 0.10.0 (2026-10-31)

### Added

- **Help desk template and the hand-off guide**. New built-in template **Help desk**: Triage answers order questions and hands billing and technical questions to Billing and Technical, with test cases for the offline model. New handbook page "Agent hand-offs" (en, vi) with a comparison of hand-offs, supervisors with workflow tools and routing nodes, and Playwright coverage of the template in the Chat tab and on the public page.
- **AI review of approvals: handbook and e2e**. A new handbook page, "AI review of
  approvals" (en, vi), covers the modes, settings, rules, when people are asked anyway, pausing, the audit, the risks
  (overconfidence, prompt injection, cost) and exports; the Human node, Agent node and Human approval pages link to it.
  A Playwright spec runs in en and vi: the settings on a Human node and an Agent's tool approval, the AI's opinion in
  the Approvals inbox, the agreement rate after a person answers, and the pause switch.
- **AI review of approvals in the editor and on the Approvals page**. Human nodes and
  Agent tool approval have an AI review section: mode (off, suggest, answer automatically; the last only for the
  workflow owner or an admin), judge credential, model and instructions, minimum confidence, daily cap, notify and
  rules, with the AI/human agreement rate. The Approvals page shows the AI's opinion on a waiting request, and an AI
  review panel lists your workflows that use it with counts, the agreement rate and a pause switch; admins also get
  the organisation pause (`GET /api/approvals/auto/workflows`). Python, TypeScript and LangGraph project exports note
  AI review; workflow export and templates keep the policy without the judge's credential.
- **AI review of approvals**. With `approval.auto` on, a waiting Human node or Agent tool call is reviewed before anyone is asked: rules first (a `reject` rule rejects, a `human` rule asks people), then a separate model call (any chat credential) that returns approve, reject or escalate with a confidence and a reason. In auto mode only a confident approval (default 0.8) answers, within a per-workflow daily cap; the AI never rejects, and errors, timeouts, invalid answers, suspected injected instructions, the demo and the cap send the request to people. Suggest mode only shows the opinion (inbox `ai`, channel messages) and records whether people agreed. Automatic answers are audited (`kind: auto`) and the run owner alone gets a `run_auto_answered` notification. `GET /api/approvals/auto/workflows/{id}` returns the 30-day counts and agreement rate.
- **Hand-offs in the code exports**. The Python file, the LangGraph project and the TypeScript file export Agent hand-offs with the same steps as the studio: `transfer_to_<agent>` tools, a hand-off node routed to the target agent, `MAX_HANDOFFS`, and a `start_agent` input that starts a run at a hand-off target.
- **Hand-offs in the studio**. The Agent node Config lists its hand-off targets with a description for the model, and sets the workflow hand-off limit. The canvas draws each hand-off as a dashed link from the Agent's hand-off handle; drawing one adds a target and deleting one removes it. The run trace and the chat steps name the agent a hand-off went to. English and Vietnamese.
- **AI review of approvals: policy and switches**. Human nodes and Agent tool approval accept `approval.auto` (`mode` off, suggest or auto; field `rules` that send to people or reject; `max_per_day`; `judge`; `min_confidence`; `notify`), checked on save. Only the workflow owner or an admin can turn auto on (`AUTO_APPROVAL_FORBIDDEN`). Kill switches: `STUDIO_AUTO_APPROVAL=off`, an organisation switch for admins and a per-workflow switch (`/api/approvals/auto`, `AUTO_APPROVAL_DISABLED`). Alembic 0045 adds the review columns to the approval audit and waiting steps.
- **Chats stay with the agent that answered**. After a hand-off, the next message of the same chat session starts at the agent that answered last (new `chat_sessions.active_agent` column). If that agent was removed or is no longer a hand-off target, the chat starts at the entry again; a new session always starts at the entry.
- **Agent hand-offs run**. An Agent with targets gets one `transfer_to_<name>` tool per target. Calling it ends the agent through a hand-off step and the target agent continues with the conversation and the reason; the run-wide hand-off limit removes the tools once reached, and other calls in the same round are answered as not run. Restarts, time travel and subgraphs keep the hand-off.
- **Agent hand-offs: targets and the limit**. An Agent node can list `handoffs` (`[{target, description}]`): other Agent nodes of the same workflow or subgraph that it may hand the conversation to. The workflow's `max_handoffs` (default 5, 0 to 20) bounds the hand-offs of a run. A hand-off target counts as reachable. Saving refuses a target that is not another Agent node of the workflow (`AGENT_HANDOFF_TARGET_INVALID`) and a limit out of range (`AGENT_HANDOFF_LIMIT`); deleting an Agent node in the editor removes it from other nodes' targets.
- **Chat attachments: handbook and e2e**. The Chat page has an Attachments section (types, limits, the state field, the file record, downloads, retention) and the error codes; the LLM and Agent node pages describe Include attachments. A Playwright spec covers attaching a PDF and an image on the published page in en and vi.

- **`sstep` alias for the CLI**. The `superstep` package also installs `sstep`, which runs the same command. The installer and the handbook CLI page mention it.
- **Chat attachments in the studio and on the page**. With attachments on, the message box has an attach button and takes dropped files. Each file is checked against the chat's kinds, size and count before upload, shows as a chip with its size (a thumbnail for images) and can be removed; Send waits for uploads. Sent messages list their files with a download action, in the Chat tab, on the published page and the widget, and in the builder's Visitors list. Chat settings gain an Attachments section bounded by the server ceiling. LLM and Agent node settings gain "Include attachments" with the files field. The published page's settings (`GET /api/public/chat/{slug}`) include `attachments` (`enabled`, `kinds`, `max_files`, `max_mb`).

- **Chat attachments reach the model**. LLM and Agent nodes have "Include attachments" (`include_attachments`, field `attachments_field`, default `files`). Documents go to the model as labelled text after the prompt. Images go as image parts to OpenAI, OpenRouter and OpenAI-compatible servers (`image_url`) and to Anthropic (`image` blocks) when the model can see images; other models get a note naming the image, and the run goes on. Image bytes are read at call time and never enter the run state. The offline mock names each file it got. The Python, LangGraph project and TypeScript exports take the same field: document text when the setting is on, and an image only when its record carries a `data_url`.

- **Chat attachments: settings and the workflow field**. Chat settings gain `attachments` (`enabled`, `kinds`, `max_files`, `max_mb`, `field`), off by default and checked against the operator ceilings (`CHAT_ATTACHMENT_LIMIT`). A message sends `attachment_ids` with its text, on the public socket and on the studio run socket. The run gets the files in the named list field as `{id, name, type, size, text?, text_cut?}`, never their bytes. Each turn lists its files. With attachments off, uploads and sends with files get `CHAT_ATTACHMENTS_OFF`. An answer to a Human node stays text only.

- **Chat attachments: storage**. A chat stores the files of a message in the database (`chat_attachments`). One file per upload, before the message is sent: `POST /api/public/chat/{slug}/sessions/{sid}/attachments` on the published page and `POST /api/chat/sessions/{sid}/attachments` in the studio, with download and delete beside them. The type is read from the bytes (PDF, PNG, JPEG, WebP, and UTF-8 `.txt`, `.md`, `.csv`). Files are served only as downloads with `nosniff`. Only the session's owner, and the builder from the Visitors list, can download them. Limits are 10 MB per file and 5 files per message, under the operator ceilings `STUDIO_CHAT_ATTACHMENT_MAX_MB` and `STUDIO_CHAT_ATTACHMENT_MAX_FILES`. Retention deletes a session's files, and files never sent are deleted after an hour. The public demo refuses uploads.

- **superstep CLI phase 2**. `login`, `logout` and `whoami` sign the CLI in with a personal access token. `pull` and `push` keep workflow JSON in a folder and refuse a studio edit since the last pull unless `--force` is set. `run` follows the run-panel socket. `test` writes JUnit XML for CI. `mcp` speaks MCP on stdio and calls the studio with that token. No new package version and no new image: the next `v*` tag ships this.

- **superstep CLI release**. `scripts/install.sh` installs the `superstep` command (`install`, `upgrade`, `backup`, `restore`, `deploy`, `doctor`, `status`, `admin`, `uninstall`). A `v*` tag publishes the Python package at the server version, and the package version moves from the `0.1.0` line to the server version. The same tag rules publish `ghcr.io/quinguyen1502/superstep-api` and `superstep-web`. The handbook Operate section starts from the CLI.

- **Agent tool calls can run together**. One round may run up to eight tool calls, then join their results in the model's order. The default is 4 at a time (`STUDIO_AGENT_PARALLEL_TOOLS`, clamped to 1–8). An Agent node can turn parallel calls off. A wave that pauses for an approval or a child run lets the other calls finish, and the parent resumes once, after every wait in that wave. The trace draws those calls as overlapping bars. The Python, LangGraph project and TypeScript exports run the round together when the setting is on.

- **Ratings on chat answers**. A visitor can mark a finished answer helpful or not, and add a short note
  when it was not. The same controls are on the embedded chat and in the studio Chat tab, where a builder can also
  rate their own chat. The Chat tab filters visitor chats that have a thumbs down, shows how the marks split over 7
  and 30 days, and can save a rated answer as a test case. When LangSmith tracing is on, the mark is sent to the
  run's trace as `user_rating`.

### Fixed

- **Run trace of a tool wave that waits in two slots**. When two calls of one round both waited (for
  example two workflow tools), the trace kept an empty row for the second slot after the run resumed. Each slot now
  keeps one row. Stale e2e specs (tool slot names, translated save errors, the template count) are updated.

- **SQLite restore and a failed upgrade rollback**. Restore deletes leftover `studio.db-wal` and `studio.db-shm` before replacing `studio.db`, so an unclean stop cannot replay old pages onto the restored file. If restoring the backup itself fails, `upgrade` reports that the rollback failed instead of saying the previous version is back. A Postgres dump is written to a file and packed from that file.

- **Chat rating races**. Two ratings of the same answer at once keep the last one. Removing a rating also removes its LangSmith feedback. Two send jobs share one feedback object.
- **Agent trace steps**. A tool slot `A/__tool/1` and the join `A/__join` sit under the Agent node. A chat hides the join step.

- **CLI secrets on a process list**. `admin create` and `admin reset-password` take a password from a prompt (`--password`) or from stdin (`--password-stdin`). `--password secret` is no longer accepted: the flag does not take a value. The password is not an argument of `superstep` or of `docker exec`. `deploy` puts `--` before the SSH host. No release tag has shipped the old flag.

- **Approval of the same node**. A new pause closes only the open wait of that node. Answering one wait of a wave leaves the others open, and the run resumes once when the last of them settles. The studio names the question it is showing, stores that answer, then closes that slot's inbox row and channel buttons, and the panel then shows the next question. The Approvals page remembers each sent row on its own. A published chat does the same with the question on the page, and the page then shows the next one. Two answers at once on SQLite both stick. The TypeScript export reads `STUDIO_AGENT_PARALLEL_TOOLS` through the same `env()` helper as the rest of the file.

- **Rating removal and LangSmith**. Deleting a chat, a workflow, or chats past the retention window also deletes the LangSmith feedback for those ratings.

- **Run status on the canvas**. The canvas now shows the run open in the Run panel. After an Agent node
  waited for a workflow tool's child run, the steps its run took afterwards, End included, are marked done. Opening a
  run from the history shows that run's marks instead of the last live run's.

## 0.9.0 (2026-10-27)

### Added

- **Workflows as Agent tools**. An Agent node can list another saved workflow as a
  tool, "Another workflow" in its tool menu: pick the workflow, the state fields the model fills and the fields it gets
  back. A workflow with its own Agent node is then a specialist agent, and the calling Agent its supervisor.
  - Each call runs as a child run of the workflow's latest saved version, linked to the calling run, which waits for
    it. A restart repeats neither the child nor its finished steps.
  - An approval inside the child appears on the Approvals page and in the channels with both workflow names
    ("Support team › Refund desk").
  - The trace shows the child's steps under the tool call. A child run says who called it.
  - Cycles and more than 5 levels of workflow tools and subgraphs are refused when saving.
  - The Python, LangGraph project and TypeScript exports write the called workflow as its own graph.
  - A new **Support team** template creates a supervisor and its Order desk and Refund desk workflows.
  - API: `GET /api/runs/{id}`; the public run result has `parent_run_id` and `waiting.child_run_id`.
  - New error code `WORKFLOW_TOOL_TOO_DEEP`.

- **Public chat page** (phase 2 of the web chat). Set **Who can chat** to *Anyone
  with the link* or *Signed-in users* and the chat gets its own page at `/c/<address>`, for people who never open the
  studio.
  - Chat settings: the page address, title, a Markdown intro, up to four suggested messages, and messages per day
    (500 by default), with Copy link and Open page.
  - Anonymous visitors are remembered by an HttpOnly cookie and see only their own chats. Signed-in chats send a
    visitor to the sign-in page and back. Each message runs the saved workflow as its owner, and the page shows only
    the steps the Chat settings allow.
  - Limits per visitor and per IP address (`STUDIO_PUBLIC_CHAT_RATE_VISITOR`, `_IP`, `_READ`, `_WINDOW`), plus the
    chat's daily cap.
  - The Chat panel lists **Visitors**' chats read-only.
  - A **logo** (PNG, JPEG or WebP, up to 256 KB) for the page header, the welcome and the browser tab. Without one,
    the page shows the title's first letter and a picture.
  - **Embed**: list the sites that may embed the chat, then paste the **chat bubble** (`/c/widget.js`, a round button
    that opens the chat and keeps the visitor's chats in every browser) or a plain **frame**.
  - API: `/api/public/chat/{slug}` (page, sessions, logo), `WS /ws/public/chat/{slug}`, `/api/public/chat-frame`, and
    `GET /api/workflows/{wid}/chat/visitors`.
  - New error codes `CHAT_NOT_PUBLISHED`, `CHAT_SLUG_INVALID`, `CHAT_SLUG_TAKEN`, `CHAT_SIGN_IN_REQUIRED`,
    `CHAT_DAILY_LIMIT`, `CHAT_EMBED_ORIGIN_INVALID`, `CHAT_LOGO_INVALID` and `CHAT_LOGO_NOT_FOUND`.

### Changed

- **The studio refuses to be framed**. Every page sends `X-Frame-Options: DENY` and
  `Content-Security-Policy: frame-ancestors 'none'`, in Compose (nginx) and in the all-in-one image. Only a published
  chat page may be framed, by the sites listed in its Chat settings.

- **Workflow checks in Vietnamese**. The editor shows the problems found when you save, open a template or
  run (a missing knowledge base, a node with no outgoing edge, a loop without a Condition…) in the UI language.
  `POST /api/validate`, saving a workflow and using a template now also return `issues`, the code of each message in
  `errors`; a run's `error` event carries them too. `errors` is unchanged.

### Fixed

- **Run trace layout**. The summary bar's items ("66 ms", "36 tokens") no longer break in two on a narrow
  panel, its divider is as tall as the text, and a workflow tool's steps sit under the tool call, lined up with the
  duration column.
- **Workflow list rows are tidier.** The access badge ("Can view") sits next to the name, and the owner shows as plain
  text after the id ("demo-approval · Shared by …") instead of a badge that ran under the Last run column. On a phone
  the Last run column gives way to a third line under the name.
- **Phone layout fixes.** Dialogs (Share, Version history, delete confirmations) stay inside the screen with long
  emails or names, and Version history stacks the list above the diff. The Code tab's toolbar wraps
  instead of pushing the page sideways. The new knowledge base form fits its card. On My accounts the Link & send code,
  Verify and Resend buttons match the input height. The user menu shows a long email in full.
- **Adding nodes on a phone.** Each Node palette card has an **Add** button; a tap on the card still works. Start and
  End now add too, as a drag does on desktop; before, a tap on them did nothing. The first card's top border is no
  longer cut off by the scroll area.
- **Demo banner in the phone editor** sits above the tab bar instead of covering it.
- **Viewers no longer see create buttons they cannot use.** The Knowledge bases tab is hidden for roles without
  `resources.manage` (an old link opens Profile), and so is "Add MCP server"; the API already refused both.
- **Public demo.** A visitor's Share dialog lists only the owner and the visitor's own row, so visitors no longer see
  each other's accounts. My accounts, the password form and the notification settings say changes are off in the demo
  and are disabled, and the language is kept in the browser instead of being sent to a server that refuses it;
  `GET /api/me` has a new `read_only` flag for that.

## 0.8.0 (2026-10-26)

### Added

- **Agent nodes in the TypeScript export**. A workflow with an Agent node, also inside a subgraph, now
  exports as LangGraph.js: the entry, model, tool and end steps as in the Python file, the studio's mock agent
  offline, LangChain.js `initChatModel` with `bindTools` when `LLM_PROVIDER` is set, and `interrupt()` before a tool
  that needs approval. MCP and knowledge base tools call stubs; built-in tools are Python functions, so they throw
  and the model is told. The error code `TYPESCRIPT_EXPORT_AGENT_UNSUPPORTED` is gone. Handbook: Agent node and
  Export to Python (en, vi).

### Changed

- **Templates say what they still need**. A workflow made from a template opens with the list of what it
  needs before it can run (for example a knowledge base for the RAG and Support agent templates), and a knowledge
  base picker with nothing chosen shows a hint, on the Retriever node and on an Agent node's knowledge base tool.

### Fixed

- **An answer accepted just before a restart is no longer lost**. With the in-memory job queue (no
  `REDIS_URL`), an answer to a waiting run (from the Approvals inbox, a chat channel, a deadline, MCP `resume_run`,
  `/api/lg` or a workflow test) only existed as a queued job: a restart before a worker took it left the run waiting,
  and the inbox and channels refused a second answer. The answer is now kept on the run (`runs.resume_job`,
  migration 0039) until the run moves on, and start-up recovery queues it again; a run cut off right after it took
  the answer goes back to waiting and resumes, instead of starting over.
- The Vietnamese label of the function picker (Tool node, an Agent node's built-in tool) is "Hàm", not "Function".
- "1 error to fix", not "1 errors to fix", in the Run panel.

## 0.7.0 (2026-10-26)

### Added

- **Workflows as MCP tools.** An MCP server at `/mcp` (official MCP Python SDK, Streamable HTTP, stateless JSON
  responses). Turn it on per workflow under **API > MCP** (off by default; route `GET`/`PUT
  /api/workflows/{wid}/mcp`); clients authenticate with the workflow's token (`Authorization: Bearer wft_...` or
  `X-Workflow-Token`) and get `run_<workflow>` (input schema from the state fields), `get_run` and `resume_run`
  (answers a run paused at a Human node). The tab copies a config for Cursor, Claude Desktop (via `mcp-remote`) or
  Claude Code. New error code `MCP_SERVER_DISABLED`. Handbook page Workflows as MCP tools (en, vi).
- **Agent node.** A model gets a task prompt and the tools you allow, decides which tool to call with which
  arguments, reads the result and repeats until it answers. Tools are MCP server tools, HTTP requests (with
  parameters the model fills), built-in Python functions and knowledge base search, each with a name and a
  description for the model. **Max rounds** (1–25, default 5) caps the loop; at the limit the model answers
  without tools. A tool marked **Needs approval** pauses the run before each call, like a Human node (run panel,
  Approvals page, approval channels, approvers, deadline): Approve runs it, Reject or a text reply tells the model
  why not. Optional steps field (every call with its arguments, result and status) and history field. Each model
  and tool call is its own checkpointed step, so a restart repeats at most the unfinished one; the run trace groups
  them by round. The offline mock drives the loop for templates, tests and the demo. Workflow tests get a **Tool
  called** check and answer Agent approvals; new built-in template **Support agent** with three test cases; the
  Python and LangGraph project exports write the loop with `interrupt()` before approved tools. The TypeScript
  export refuses Agent nodes for now. Error codes `AGENT_TOOLS_UNSUPPORTED`,
  `TYPESCRIPT_EXPORT_AGENT_UNSUPPORTED`. Handbook: Agent node (en, vi), and the node reference, MCP, approvals,
  tests, traces, chat, templates, export and comparison pages.
- **Runs survive a restart without Redis.** With the in-memory job queue (no `REDIS_URL`), the server now queues
  every `queued` or `running` API, schedule, chat or test run again at start-up, and the worker continues it from
  its last progress checkpoint, as Redis lease recovery already did. A run taken `STUDIO_RECOVER_MAX_ATTEMPTS`
  times (default 3) ends as `error` with the new code `RUN_INTERRUPTED`. `STUDIO_RECOVER_ON_START=0` turns it off.
  Runs paused at a Human node already survived restarts (their checkpoint is in the database); tests now restart a
  real server process between pause and resume. Handbook: Runs across restarts (en, vi); the comparison pages'
  durable-runs cells say what continues after a restart.
- **Handbook: two comparison pages** (en, vi), next to Superstep vs LangSmith. **Superstep vs visual builders**
  compares Superstep with n8n, Dify, Langflow and Flowise (what runs under the canvas, license, hosting, human in the
  loop, durable runs, evals and observability, API and code export). **Superstep vs agent frameworks** compares
  Superstep plus LangGraph with the code-first frameworks CrewAI and PydanticAI. Both cite each project's docs and
  license file and say when to choose another tool.

### Changed

- **Phone layout.** Below 768px the workflow list and Settings fit the screen, and the editor shows one pane at a
  time (Canvas, Nodes, Config, Run, Chat) with a tab bar at the bottom. The header keeps Save, Run, Chat and the ⋯
  menu as icons, a tap on a palette card adds that node, and the run input sits above the logs. Wider screens keep
  the side-by-side panels.
- **Intro video.** The handbook home page video (en, vi, 91 s) shows the current editor, with the Config tabs, and
  ends with a new chapter on the Agent node (Support agent template, an approved tool call, rounds in the trace),
  time travel, the workflow as an MCP tool and the phone layout. The quickstart screenshots are recaptured.
- **Node Config tabs.** Every node's Config shows the same three tabs in the same order: **Settings** (what the node
  does), **Data** (every state field it reads or writes, and its input fields) and **Execution** (retry, timeout,
  cache, round and item limits). A tab the node does not use stays in place, disabled; the chosen tab stays open
  when you select another node; a dot marks a missing output field or an Agent without tools. Handbook: Nodes >
  Config tabs (en, vi).

### Fixed

- **Time travel after a Condition.** A node that ran after a node leaving the state unchanged (a Condition) was
  grouped into that node's checkpoint, so forking there ran both, the old branch included, and End twice. Each
  `node_finished` event now carries its `superstep`, and checkpoints follow it (older runs keep the old grouping).
- **Restart recovery and resumed runs.** Each resume after a Human node or an Agent tool approval counted toward
  `STUDIO_RECOVER_MAX_ATTEMPTS`, so a run that had been resumed a few times ended as `RUN_INTERRUPTED` at its first
  restart. Only restarts that cut the run off count now.

## 0.6.0 (2026-10-24)

### Added

- **Handbook: Superstep vs LangSmith** (en, vi). A comparison with LangSmith Studio and LangSmith Agent Builder
  (what each is for, pricing and hosting, how the LangGraph interop features work with LangSmith), citing
  LangChain's Studio docs, pricing page, self-hosted overview and the Agent Builder GA post.
- **Time travel in the Run panel.** **Time travel** on a finished run lists its checkpoints (the nodes that ran
  next and the state before them, then the final state); inspect or edit a state and **Fork from here** to start
  a new run at those nodes. The fork runs the original run's stored version, keeps iteration counts and records
  `forked_from` on its `run_started` event. Route `GET /api/runs/{run_id}/checkpoints`, WebSocket request
  `{"fork": {run_id, checkpoint, state?}}`; error codes `CHECKPOINT_NOT_FOUND`, `RUN_FORK_UNSUPPORTED`.
- **LangSmith evals and trace links (opt-in).** With `LANGSMITH_API_KEY` set and the admin setting **Send test
  results to LangSmith** on, each finished workflow test run goes to LangSmith: the test cases as a dataset (kept
  in sync) and the run as an experiment with `passed` and per-check feedback; a **LangSmith** menu (Open in
  LangSmith, Send to LangSmith) in the Tests panel, whose toolbar now uses one outline style and default sizes. Runs traced to LangSmith (`LANGSMITH_TRACING=true`) link to their LangSmith
  trace when `STUDIO_TRACE_URL` is not set. Routes `GET|PUT /api/admin/langsmith`,
  `POST /api/workflows/{wid}/tests/runs/{sid}/langsmith`; columns `runs.trace_root`,
  `workflow_test_suites.langsmith_url` (migration 0037); error codes `LANGSMITH_NOT_CONFIGURED`,
  `LANGSMITH_PUSH_FAILED`.
- **LangGraph Agent Server API (subset) at `/api/lg`.** The official `langgraph-sdk` clients and `RemoteGraph` can
  run Superstep workflows: assistants (one per workflow: search, get, graph, schemas), threads (create, get, search,
  delete, state, history), runs (create, wait, stream with `values` / `updates`, get, list, join, cancel, also
  without a thread), Human nodes as interrupts resumed with `Command(resume=...)`. Auth with a workflow token or a
  user JWT (`x-api-key`, `X-Workflow-Token` or `Authorization: Bearer`). New tables `agent_threads` and
  `agent_thread_runs` (migration 0036), error codes `THREAD_NOT_FOUND`, `THREAD_EXISTS`, `THREAD_BUSY`,
  `THREAD_WORKFLOW_MISMATCH`. Handbook page **LangGraph-compatible API** (en, vi); design in
  `docs/agent-server-api.md`; live check `scripts/agent_server_smoke.py`.
- **LangGraph project export.** The Code tab's **Project .zip** button (and
  `GET /api/workflows/{wid}/export/{language}/project`) saves the Python or LangGraph.js export as a runnable project:
  `langgraph.json`, the graph module with a module-level `graph`, `requirements.txt` + `pyproject.toml` or
  `package.json`, `.env.example` and a README. It runs with `langgraph dev` (Python `langgraph-cli[inmem]`, JS
  `@langchain/langgraph-cli`) and opens in LangSmith Studio; `scripts/langgraph_dev_smoke.py` checks both with the
  official `langgraph-sdk`.
- **Public API and SDKs.** The two workflow-trigger routes (`POST /api/hooks/workflows/{wid}/runs`,
  `GET /api/hooks/workflows/{wid}/runs/{run_id}`) now have a full OpenAPI contract: `WorkflowToken` (`X-Workflow-Token`)
  and `WorkflowBearer` security schemes, typed request and response models, error-envelope responses with examples,
  operation ids `startRun` / `getRun` and a `public` tag. A public-only spec is served at `/openapi.public.json` with a
  Swagger view at `/docs/public`, and committed as `docs/api/openapi.public.json` by `scripts/gen_public_openapi.py`
  (a test fails when it is stale). An async start now also sends the poll URL in the `Location` header.
- **Python SDK** (`sdk/python`, package `superstep`): sync and async clients on httpx, typed models, `run`, `get_run`,
  `wait`, `run_and_wait` with timeout and poll backoff, errors typed by error code, env var fallback.
- **TypeScript SDK** (`sdk/typescript`, `@superstep/sdk`): fetch-based, zero runtime dependencies, ESM and CommonJS,
  types generated from the public spec (`npm run gen`), `run`, `getRun`, `wait`, `runAndWait`, AbortSignal support.
- Both SDKs have unit tests and a live test against a local backend (`scripts/sdk_integration.sh`), run on CI; a
  tag-triggered publish workflow (`sdk-py-v*`, `sdk-ts-v*`) is ready but needs the registry setup in `sdk/README.md`.
- Handbook: **Public API and SDKs** guide and a **Public API reference** page rendered from the spec with a vendored
  Redoc bundle (works offline), in English and Vietnamese.

### Changed

- The offline mock model answers in the requester's UI language: English by default, Vietnamese when the studio is in
  Vietnamese (the studio sends `locale` with run and chat requests; `Accept-Language` is the fallback). The example
  `lookup_order` tool follows it too, and exported code's mock now answers in English. README overview screenshots
  regenerated, so the English one shows English replies.
- Public demo: each "Try the demo" sign-in gets an anonymous visitor account of its own, so run history, chats, waiting
  runs and notifications are no longer shared between visitors; the samples stay shared and read-only. Visitors older
  than `STUDIO_DEMO_VISITOR_TTL` (default one day) are removed with their runs and chats.

### Fixed

- Flaky tests: the parallel Human-sibling test accepts both valid orders (LangGraph cancels siblings that have not
  started when the Human node pauses), the process-group test skips with a reason when the host's process limit
  prevents the fork, the credentials e2e waits for the list before deleting, the Code time-limit bound allows a slow
  CI runner, and the compose smoke waits for `run_summary` before reading run history.
- `factory validate` is clean again: the factory verification workflow is the generated one (it no longer runs on
  pushes to `main`; release PRs still run it) and merged tasks are filed as done.

### Removed from known limits

- Demo visitors no longer see each other's run history and chats, and mock replies are no longer always Vietnamese.

## 0.5.0 (2026-10-24)

### Added

- **Web chat** (phase 1). Backend: chat sessions and messages, a web chat trigger with Chat settings (input,
  reply and history fields, steps shown to visitors, turns and retention), Human nodes answered by the person chatting
  or by a reviewer (#116, migration `0035_chat_sessions`). Studio: a Chat side panel beside the canvas (Chat button or
  Shift+C, 340–760 px, fullscreen with the list of chats), a session picker and New chat, **View as** Workflow builder /
  Chat visitor with a preview banner, tool steps and confirmations in the thread (#117).
- **Editor layout**: the bottom panel is Run · Test · Code; Run shows the input and the logs side by side with a run
  picker and **View all**; Config folds away on narrow screens (#117).
- **Alignment guardrails**: rule 11 in `docs/ui-conventions.md`, `npm run lint:ui` on CI,
  `e2e/alignment.spec.ts`; Badge and TabsList `size="sm"`; ScrollArea content no longer overflows its panel (#118).
- **PaaS deploys**: an all-in-one image (UI, API and WebSocket on one port) with Render and Heroku buttons, Railway,
  Coolify and Dokploy configs (#119); Fly.io, DigitalOcean, Koyeb, Zeabur, Northflank and a self-hosted guide, image CI
  (#120); a remote sandbox service so Code nodes can run isolated where the platform has no Docker (#121).
  Guides in `docs/deploy/`.
- **Public demo mode** (`STUDIO_DEMO_MODE`): a shared read-only visitor with "Try the demo", seeded samples (the
  Chatbot with web chat on), Code, HTTP and Send email nodes off, mock models, a per-IP run limit (unit-tested) and a demo banner; visitors can chat with the Chatbot;
  the live demo runs on Render (#122).

### Changed

- README restyled: centred header, overview screenshot, feature table; handbook screenshots and text refreshed for the
  new layout and the chat panel (#117).

### Fixed

- The editor top bar no longer overlaps or half-clips its info badges at 1440 px (the demo viewer in Vietnamese was the
  tightest case): the LLM mode and id badges hide whole when they do not fit; `e2e/alignment.spec.ts` checks the bar for
  an admin and a viewer in en and vi.
- Demo-mode node errors ("… nodes are turned off in the public demo") no longer carry a stray `AppError: ` prefix.
- README feature-row captions are no longer clipped.

### Known limits

- In the public demo every visitor shares one account, so the run history and chats are shared until the next reset
  (`docs/deploy/demo.md`).

### Earlier (0.4.0)

- TypeScript in Code mode on Deno and the LangGraph.js export shipped in 0.4.0 (#109–#112).
