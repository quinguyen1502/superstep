# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0044
- Status: Implemented (TASK-0074 PR #98, TASK-0075 PR #99, TASK-0076 PR #100, TASK-0077 PR #101)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-22
- Updated: 2026-10-22
- Source: owner request in chat, 2026-10-22 ("Do proposal 6"). Proposal 6 from the suggestion list was to use
  channels as triggers: a message to the Slack or Telegram bot runs a workflow. The channels are already connected,
  but the feature touches many parts. The owner had set it aside ("Bigger, later") and picked it up after REQ-0043.

## Summary

- A **chat trigger** starts a workflow from a message to the Slack app or the Telegram bot that is already connected
  for approvals. An example message is `@Superstep leave I'd like Friday off`.
- The bot answers in the same thread: it says the run started, then gives the result (or the error, or that the run
  is waiting for an approval) with a link to the run.
- Chat triggers are set per workflow in a **Chat triggers** dialog, next to API tokens and schedules.

## Problem Or Opportunity

- Today a run starts from the studio, the API trigger (REQ-0004, tokens) or a schedule (REQ-0033). People who work in
  Slack or Telegram need a token and an HTTP client, or an extra service, to start a workflow from a chat.
- The bots already talk to these people for approvals (REQ-0034, DEC-0019): the connections, signatures and verified
  chat identities exist. They only listen for button presses, not for messages.

## Scope

### In Scope

- **Platforms:** Slack and Telegram, through the connections that already exist (personal or org, DEC-0019).
- **Trigger settings** (per workflow, stored as rows like schedules):
  - the connection (a Slack workspace or a Telegram bot the user may use);
  - where it listens: a Slack channel, a Telegram group, or direct messages to the bot;
  - the command word;
  - the input field that gets the message text;
  - the state field the reply shows;
  - on or off.
- **Receiving messages:**
  - **Slack:** the Events API (`app_mention` in channels, `message.im` in direct messages) at a new shared events URL.
    It is routed by `team_id` and verified with the signing secret. It answers Slack's `url_verification`, replies
    within 3 s and queues the work. Slack's retries are dropped by `event_id`.
  - **Telegram:** the bot's existing webhook. Telegram allows one webhook per bot, so messages arrive at the same URL
    as button presses. "Register webhook" also asks for `message` updates.
  - Messages from bots, edits, files and messages that match no trigger are ignored silently.
- **Who may run:** a verified chat identity (the existing identity linking, `IdentityService`) whose studio user may
  run the workflow (Q1).
- **Runs:**
  - Runs go through the job queue with `source="chat"`. They have the run's owner, the trigger and the sender's chat
    account.
  - They are rate-limited per sender and trigger, like API tokens.
  - A run uses the workflow owner's credentials and resources, as every saved-workflow run does (DEC-0023).
- **Replies in the thread:**
  - **Started:** a short note with the run link.
  - **Finished:** the chosen field's value, shortened to the platform's limit, with a link to the run.
  - **Error:** the error message.
  - **Waiting:** "waiting for approval at <node>". The approval request itself goes where the Human node sends it, as
    today.
  - **Refused:** the message is not linked, has no run right, is rate-limited, or the workflow is gone. The refusal
    goes to the sender only (a Slack ephemeral message, a Telegram direct reply), in their language (en, vi).
- **Editor:**
  - A **Chat triggers** dialog in the ⋯ menu and the command palette.
  - It lists, adds, edits, switches on or off, and deletes triggers. Delete asks the user to type the name.
  - It shows the trigger's last message time and last run.
  - Managing triggers needs the workflow's share right (owner or admin), as for schedules and tokens.
- **Run history:** a "chat" source badge with the platform. The run detail shows who sent the message.
- **Setup:**
  - The Slack app needs the scopes `app_mentions:read` and `im:history` and an Event Subscriptions URL.
  - "Add to Slack" asks for the new scopes. Existing workspaces must reinstall the app.
  - The Channels page shows the events URL and warns when a connection lacks the scopes.
- **Handbook** (en, vi): a "Chat triggers" page with Slack and Telegram setup and a screenshot. The Channels and API
  trigger pages link to it.

### Out Of Scope

- WhatsApp, Microsoft Teams and e-mail triggers. WhatsApp and Teams could follow on the same model.
- Slack slash commands (Q2 chose a command word).
- Answering a Human node by typing in the thread. Approvals keep their buttons and links.
- Conversations: a follow-up message is a new run, with no chat memory.
- Files, images and voice messages as input.
- Streaming each node's progress into the chat.
- Starting a run as someone with no studio account (Q1).

## Stakeholders Or Users

- Team members who live in Slack or Telegram and start routine workflows (leave requests, summaries, lookups).
- Workflow owners, who decide which workflow a chat may start and what the reply shows.
- Admins, who manage org connections and the Slack app's scopes.

## Current Context

- **Connections and adapters:**
  - `backend/app/services/channel_service.py` and `services/approval_channels/` (`base.py`, `slack.py`,
    `telegram.py`) hold the adapters.
  - Each adapter can `verify` a callback, `handle_callback` a button press and `send_dm`.
  - Slack uses one shared callback routed by `team_id`. Telegram `register` sets the webhook with
    `allowed_updates: ["callback_query"]`.
- **Callbacks:** `api/routes/approvals.py` receives `POST /api/approvals/callback/{kind}[/{cid}]`, and
  `ApprovalService.handle_callback` handles it.
- **Identities:** `services/identity_service.py` (DM code, verified links per platform and Slack workspace).
  `ApprovalRepository.user_for` returns the studio user of a verified account.
- **Slack OAuth:** `services/slack_oauth.py`, with `config.SLACK_BOT_SCOPES = "chat:write,chat:write.public,im:write"`.
- **Triggers:**
  - `services/trigger_service.py` (tokens, `start`, rate limit, `run_result`).
  - `services/schedule_service.py` (rows per workflow, share right, `source="schedule"`).
  - `services/run_worker.py` (the job queue, `RunService.settled`).
  - `services/delivery_service.py` (callback after a run settles).
- **Editor:** `frontend/src/components/schedules-dialog.tsx` and `api-trigger-dialog.tsx`. The commands live in
  `components/editor/use-studio.ts` (`action:schedules`, ⋯ menu).
- **Decisions:** DEC-0019 (approval channels), DEC-0023 (owner's resources), DEC-0036 (schedules).

## Desired Behavior

- An owner opens **Chat triggers** on the Leave request workflow and adds a trigger with these settings:
  - connection: the "Acme" Slack workspace;
  - where: the `#hr` channel;
  - command word: `leave`;
  - input field: `request`;
  - reply field: `decision`.
- Bo has linked and verified their Slack account in Profile. Bo writes `@Superstep leave I'd like Friday off` in
  `#hr`. In the thread, the bot replies "Started *Leave request* · open run". The manager gets the approval request
  as today.
- When the manager approves, the thread gets "Leave request finished: approved · open run".
- An unlinked colleague sends the same message. Only they see "Link your Slack account in Superstep (Profile → Chat
  accounts) to run workflows", and no run starts.
- In a direct message to the Telegram bot, `summary <text>` runs the Customer feedback digest, and the bot replies
  with the `report` field.
- The owner switches the trigger off. The next `leave` message gets "This trigger is off" (sender only).

## Business Rules

- A message starts at most one run. Platform retries and duplicate deliveries start nothing new.
- Only verified chat identities whose studio user may run the workflow start runs (Q1). Everything else is
  refused to the sender only and audited.
- Command words are unique per connection and place, so two triggers never answer the same message.
- The reply never holds secrets. It shows only the chosen field and the run link.
- Managing triggers needs the share right. A trigger stops (note on the row, like schedules) when its creator loses
  that right, when its connection is deleted or when the workflow is deleted.
- Errors:
  - New codes go in `CATALOG`, `docs/api-errors.md` and both locales.
  - Expected codes: `CHAT_TRIGGER_NOT_FOUND`, `CHAT_TRIGGER_COMMAND_TAKEN`, `CHAT_TRIGGER_LIMIT`, and
    `CHAT_TRIGGER_SCOPE_MISSING` (Slack scopes).
- Delete asks for the typed name (UI rule 7).

## Constraints

- Backend layers (DEC-0009), with an Alembic migration for the trigger table and any run columns.
- No new dependency.
- The adapter interface grows with message parsing and threaded replies. Business rules stay in a service, as for
  approvals.
- Slack's 3-second limit: the events route verifies, records and queues. It never runs the workflow inline.
- shadcn components and theme tokens, en and vi locale keys identical, `api()` only.

## Acceptance Criteria

- A Slack `app_mention` with a known command from a verified, permitted user starts exactly one run with
  `source="chat"`. Tests send the same event twice (Slack retry headers) and still get one run.
- A Telegram message to the bot does the same. Button presses on the same webhook still decide approvals.
- The thread gets the "started" note and, after the run settles, the result, error or waiting note. A run that waits
  and later finishes posts the result when it finishes.
- Each kind of refusal is answered only to the sender, in their language, and audited:
  - not linked;
  - not verified;
  - no run right;
  - trigger off;
  - rate-limited;
  - workflow deleted.
- Bad signatures, stale timestamps and other workspaces' events are rejected as for approval callbacks.
- The dialog lists, adds, edits, switches on and off, and deletes (typed name) triggers. A duplicate command word is
  refused with a message.
- Run history shows the chat source and the sender.
- The handbook page (en, vi) with a screenshot passes the strict builds and the image check.
- pytest (SQLite and Postgres), the layer test, lint, typecheck, vitest, build and e2e pass. Slack and Telegram are
  faked with `httpx.MockTransport`, as in the approval tests.

## Edge Cases

- A message with the command word only and no text: the input field gets "". The workflow's own validation decides
  what happens.
- Text longer than the run input limit: refused (`RUN_INPUT_TOO_LARGE`), answered to the sender.
- The command word in another case (`Leave`), or after the mention, a colon or extra spaces: matched.
- The same bot in several Telegram groups: the trigger's group id decides.
- A Slack workspace connected both personally and org-wide: the trigger names one connection, and the events URL
  routes by `team_id` to it.
- A message edited after sending: ignored. Only new messages count.
- The trigger's connection is deleted, or the Slack app is reinstalled without the scopes: the trigger shows a note,
  and messages are ignored.
- A reply field that holds a list or an object: shown as compact JSON, shortened.
- The workflow is in a team or shared: the run right is checked through `AccessService`, as for the studio.

## Assumptions

- The approval connections are the right home for this. Owners do not want a second bot or token per platform.
- Replying in the thread with a run link is enough feedback. The full trace stays in the studio.
- Slack workspaces that use approvals can reinstall the app to add two read scopes.

## Open Questions

`.factory-state/artifacts/CLAR-0002-chat-triggers.md`: the owner answered all four questions on 2026-10-22 and picked
the recommended option each time:

- **Q1. Who may start a run from a chat?** Only people with a verified linked chat account whose studio user may run
  the workflow. The run belongs to that user.
- **Q2. How does a message pick its workflow?** A command word: `@bot leave <text>` in a channel or group, and
  `leave <text>` in a direct message.
- **Q3. What does the bot reply when the run ends?** The value of one state field chosen on the trigger, with a link
  to the run.
- **Q4. How does the message become run input?** The text after the command word goes into one input field chosen
  on the trigger.

## Related Artifacts

- `.factory-state/artifacts/REQ-0034-more-approval-channels.md` (connections, adapters)
- `.factory-state/artifacts/REQ-0033-scheduled-runs.md` and `.factory-state/decisions/DEC-0036-scheduled-runs.md`
  (per-workflow trigger rows, share right)
- `.factory-state/artifacts/REQ-0041-approval-deadlines-and-inbox.md` (Human nodes, inbox)
- DEC-0019 (approval channels), DEC-0023 (owner's resources)
- Tasks: TASK-0074 (settings and API), TASK-0075 (messages, runs, replies), TASK-0076 (editor and Channels page),
  TASK-0077 (handbook)
- `roadmap.md`
