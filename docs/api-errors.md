# API response envelope and error codes (DEC-0010)

## Envelope (every REST endpoint)

```jsonc
// success
{"success": true, "data": <payload>, "error": null}
// error
{"success": false, "data": null, "error": {"code": "AUTH_INVALID_CREDENTIALS", "message": "Incorrect email or password", "details": <optional>}}
```

- `meta` is reserved for later use (e.g. pagination) and is not sent today.
- `code` is stable UPPER_SNAKE and is the contract. `message` is English and for humans/logs only. Clients translate by `code` and fall back to `message`.
- `details`: 422 → `[{"field": "nodes.0.id", "message": "..."}]`; `WORKFLOW_INVALID` → list of validator messages.
- An expired token returns `AUTH_TOKEN_EXPIRED` **and** the header `X-Auth-Error: expired`.
- Unhandled exceptions → 500 `INTERNAL_ERROR` (logged; no internals in the message).

## Implementation (one place each)

| Concern | Where |
|---|---|
| Code catalog (single source of truth: status + English message template) | `backend/app/core/errors.py` `CATALOG` |
| Raising | `raise AppError("CODE", details=..., **template_params)`; no per-route try/except |
| Success wrapping | `schemas/envelope.py` `EnvelopeResponse` (FastAPI `default_response_class`) |
| Error wrapping | `api/error_handlers.py`: one handler each for AppError, 422, HTTP 404/405, unhandled Exception |
| Frontend unwrap | `frontend/src/lib/api.ts` `api()` |
| Frontend translation | `frontend/src/locales/{en,vi}.json` → `errors.<CODE>`; `lib/i18n.ts` `errorText()` |

`backend/tests/test_api_envelope.py` checks that every catalog code appears in this table and in both locale files.

<!-- --8<-- [start:catalog] -->
## WebSocket `/ws/run` error events

```jsonc
{"type": "error", "error": {"code": "NODE_FAILED", "message": "...", "details": [...]}, "errors": ["..."], "node": "classify", ...}
```

`errors` (a list of strings) is kept for the trace UI and stored history. An auth failure still closes with code **4401**. A timeout event carries `status: "timeout"` and code `RUN_TIMEOUT`.

## Code catalog

| Code | HTTP | English message |
|---|---|---|
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `BAD_REQUEST` | 400 | Bad request |
| `NOT_FOUND` | 404 | Resource not found |
| `METHOD_NOT_ALLOWED` | 405 | Method not allowed |
| `PAYLOAD_TOO_LARGE` | 413 | Payload too large |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `AUTH_REQUIRED` | 401 | Authentication required |
| `AUTH_TOKEN_INVALID` | 401 | Invalid token |
| `AUTH_TOKEN_EXPIRED` | 401 | Session expired, please sign in again |
| `AUTH_INVALID_CREDENTIALS` | 401 | Incorrect email or password |
| `AUTH_EMAIL_INVALID` | 400 | Invalid email address |
| `AUTH_EMAIL_TAKEN` | 409 | Email is already registered |
| `AUTH_PASSWORD_TOO_SHORT` | 400 | Password must be at least {min} characters |
| `AUTH_PASSWORD_TOO_LONG` | 400 | Password must be at most {max} characters |
| `AUTH_PASSWORD_WEAK` | 400 | Password must contain both letters and digits |
| `AUTH_LOCKED` | 429 | Too many failed sign-ins. Try again in {minutes} min |
| `AUTH_PASSWORD_WRONG` | 400 | The current password is incorrect |
| `AUTH_PASSWORD_SAME` | 400 | The new password must be different from the current one |
| `AUTH_CSRF` | 403 | Missing X-Requested-With header |
| `PASSWORD_RESET_INVALID` | 400 | This reset link is invalid or has expired |
| `WORKFLOW_NOT_FOUND` | 404 | Workflow not found |
| `WORKFLOW_FORBIDDEN` | 403 | You do not have access to this workflow |
| `WORKFLOW_NAME_REQUIRED` | 400 | Workflow name is required |
| `WORKFLOW_NAME_TOO_LONG` | 400 | Workflow name must be at most {max} characters |
| `WORKFLOW_NAME_TAKEN` | 409 | A workflow with this name already exists |
| `WORKFLOW_TOO_LARGE` | 413 | Workflow is too large (max {max_kb} KB) |
| `WORKFLOW_INVALID` | 400 | Workflow is invalid |
| `TEMPLATE_NOT_FOUND` | 404 | Template not found |
| `TEMPLATE_READ_ONLY` | 403 | This template cannot be deleted |
| `TEMPLATE_INVALID` | 400 | Not a valid template file |
| `TEMPLATE_NAME_REQUIRED` | 400 | Template name is required |
| `TEMPLATE_SCOPE_FORBIDDEN` | 403 | Only administrators can share templates with the whole organisation |
| `RUN_REQUEST_INVALID` | 400 | Run request must be a JSON object |
| `RUN_INPUT_INVALID` | 400 | Run input must be a JSON object |
| `RUN_INPUT_TOO_LARGE` | 413 | Run input is too large (max {max_kb} KB) |
| `RUN_FAILED` | 500 | Run failed |
| `RUN_TIMEOUT` | 408 | Run exceeded the time limit ({seconds}s, STUDIO_RUN_TIMEOUT) |
| `RUN_NOT_FOUND` | 404 | Run not found, already finished or not yours |
| `THREAD_NOT_FOUND` | 404 | Thread not found or not yours |
| `THREAD_EXISTS` | 409 | A thread with this id already exists |
| `THREAD_BUSY` | 409 | The thread already has a run in progress |
| `THREAD_WORKFLOW_MISMATCH` | 409 | The thread belongs to another workflow |
| `LANGSMITH_NOT_CONFIGURED` | 400 | LangSmith is not configured: set LANGSMITH_API_KEY on the server |
| `LANGSMITH_PUSH_FAILED` | 502 | Sending to LangSmith failed ({reason}) |
| `RUN_NODE_NOT_REACHED` | 400 | The run finished without reaching node '{node}' |
| `NODE_FAILED` | 500 | Node failed |
| `HTTP_TOOL_URL_BLOCKED` | 400 | HTTP Tool node {node}: the URL must be a public http(s) address |
| `TEMPLATE_REF_INVALID` | 400 | Template error: {reason} |
| `CREDENTIAL_NOT_FOUND` | 404 | Credential not found or not yours |
| `CREDENTIAL_PROVIDER_UNSUPPORTED` | 400 | Unsupported provider: {provider} |
| `CREDENTIAL_KEY_REQUIRED` | 400 | API key is required |
| `CREDENTIAL_BASE_URL_INVALID` | 400 | Base URL must start with http:// or https:// |
| `CREDENTIAL_DECRYPT_FAILED` | 500 | Could not decrypt credential (was the secret key changed?) |
| `PROVIDER_UNREACHABLE` | 502 | Could not reach {provider} at {base_url}: is the server running and reachable from the API? |
| `PROVIDER_AUTH_FAILED` | 400 | {provider} rejected the API key: {reason} |
| `PROVIDER_BAD_RESPONSE` | 502 | {provider} returned an unexpected response: {reason} |
| `MODEL_NOT_FOUND` | 400 | {provider} has no model named {model} |
| `CREDENTIAL_HEADER_UNSUPPORTED` | 400 | {provider} does not accept the header {header} |
| `PROVIDER_EMBEDDINGS_UNSUPPORTED` | 400 | {provider} does not provide embeddings; choose another credential for this knowledge base |
| `AGENT_TOOLS_UNSUPPORTED` | 400 | {provider} cannot call tools; choose a credential with tool calling for this Agent node |
| `KB_EMBEDDING_DIMENSION_MISMATCH` | 409 | The embedding model returns {got}-dimensional vectors but this knowledge base stores {expected}-dimensional ones; re-index the knowledge base |
| `KB_NOT_FOUND` | 404 | Knowledge base not found or not yours |
| `KB_NAME_REQUIRED` | 400 | Knowledge base name is required |
| `KB_NAME_TOO_LONG` | 400 | Knowledge base name must be at most {max} characters |
| `KB_DOCUMENT_NOT_FOUND` | 404 | Document not found |
| `KB_FILE_REQUIRED` | 400 | Choose a file to upload |
| `KB_FILE_TYPE_UNSUPPORTED` | 400 | Unsupported file type (allowed: {allowed}) |
| `KB_FILE_TOO_LARGE` | 413 | File is too large (max {max_mb} MB) |
| `KB_FILE_UNREADABLE` | 400 | Could not read the file: {reason} |
| `KB_FILE_EMPTY` | 400 | The file contains no text |
| `KB_QUERY_REQUIRED` | 400 | Enter a search query |
| `KB_EMBEDDING_FAILED` | 502 | Embedding failed: {reason} |
| `KB_EMBEDDER_CHANGED` | 409 | The embedding model or key changed since the documents were indexed; re-index the knowledge base |
| `MCP_SERVER_NOT_FOUND` | 404 | MCP server not found |
| `MCP_NAME_REQUIRED` | 400 | MCP server name is required |
| `MCP_NAME_TOO_LONG` | 400 | MCP server name must be at most {max} characters |
| `MCP_TRANSPORT_UNSUPPORTED` | 400 | Unsupported MCP transport: {transport} |
| `MCP_CONFIG_INVALID` | 400 | MCP server setting {field} is missing or invalid |
| `MCP_URL_INVALID` | 400 | The MCP server URL must be a public http(s) URL |
| `MCP_STDIO_DISABLED` | 403 | stdio MCP servers are disabled on this server (STUDIO_MCP_STDIO) |
| `MCP_ADMIN_REQUIRED` | 403 | Only an admin can manage stdio or organization MCP servers |
| `MCP_CONNECT_FAILED` | 502 | Could not talk to the MCP server: {reason} |
| `MCP_TOOL_NOT_FOUND` | 404 | The MCP server has no tool named {tool} |
| `MCP_TOOL_FAILED` | 502 | The MCP tool failed: {reason} |
| `MCP_ARGUMENT_INVALID` | 400 | Argument {name} must be of type {type} |
| `IMPORT_SOURCE_REQUIRED` | 400 | A GitHub URL or a zip file is required |
| `IMPORT_ZIP_TOO_LARGE` | 413 | Zip file is too large (max 50 MB) |
| `IMPORT_INVALID` | 400 | Import failed: {reason} |
| `IMPORT_JOB_NOT_FOUND` | 404 | Import job not found |
| `IMPORT_NOT_READY` | 400 | Import job is not ready or the graph is invalid |
| `IMPORT_DISABLED` | 404 | Repo import is disabled (set STUDIO_ENABLE_IMPORT=1 to enable this experimental feature) |
| `AUTH_ACCOUNT_DISABLED` | 403 | This account has been deactivated |
| `PERMISSION_DENIED` | 403 | Your role does not allow this ({permission}) |
| `USER_NOT_FOUND` | 404 | User not found |
| `USER_ROLE_INVALID` | 400 | Role must be one of: {roles} |
| `USER_LAST_ADMIN` | 409 | The studio needs at least one active admin |
| `USER_SELF_CHANGE` | 409 | You cannot change your own role or deactivate your own account |
| `SHARE_USER_NOT_FOUND` | 404 | No active account with that email |
| `SHARE_ROLE_INVALID` | 400 | Share role must be viewer or editor |
| `SHARE_OWNER` | 400 | The owner already has full access |
| `SHARE_NOT_FOUND` | 404 | This workflow is not shared with that user |
| `SLACK_OAUTH_NOT_CONFIGURED` | 503 | Add to Slack is not configured (SLACK_CLIENT_ID / SLACK_CLIENT_SECRET) |
| `SLACK_OAUTH_STATE_INVALID` | 400 | The Slack sign-in link is invalid or expired, please try again |
| `SLACK_OAUTH_FAILED` | 502 | Slack did not complete the installation: {reason} |
| `TEAM_NOT_FOUND` | 404 | Team not found |
| `TEAM_NAME_REQUIRED` | 400 | Team name is required |
| `TEAM_NAME_TAKEN` | 409 | A team with this name already exists |
| `TEAM_MEMBER_NOT_FOUND` | 404 | This user is not a member of the team |
| `TRANSFER_SAME_OWNER` | 400 | This user already owns the workflow |
| `TRANSFER_TARGET_ROLE` | 400 | The new owner must be an editor or an admin |
| `TRANSFER_REBIND_INVALID` | 400 | Node {node}: choose a resource the new owner can use |
| `USER_HAS_WORKFLOWS` | 409 | This user owns {count} workflow(s): choose who takes them over first |
| `USER_DELETE_MODE_INVALID` | 400 | Mode must be anonymize or delete |
| `WORKFLOW_IN_USE` | 409 | {count} workflow(s) use this workflow as a subgraph |
| `ORG_RESOURCE_NOT_ALLOWED` | 403 | Your role may not use organization-wide resources at run time ({kind}) |
| `CREDENTIAL_SETTINGS_INVALID` | 400 | Check the setting {field} |
| `EMAIL_HOST_BLOCKED` | 400 | The SMTP host {host} is a private or local address (allowed only with STUDIO_SMTP_ALLOW_PRIVATE=1) |
| `EMAIL_AUTH_FAILED` | 400 | The SMTP server rejected the sign-in: {reason} |
| `EMAIL_SEND_FAILED` | 502 | The e-mail could not be sent: {reason} |
| `EMAIL_CREDENTIAL_INVALID` | 400 | Send email node {node}: choose an SMTP credential |
| `EMAIL_RECIPIENT_INVALID` | 400 | Send email node {node}: '{address}' is not an e-mail address |
| `EMAIL_RECIPIENTS_MISSING` | 400 | Send email node {node}: there is no recipient (To, Cc or Bcc) |
| `EMAIL_TOO_MANY_RECIPIENTS` | 400 | Send email node {node}: at most {max} recipients |
| `EMAIL_RATE_LIMITED` | 429 | Send email nodes may reach {limit} recipients per hour; try again in {retry} s |
| `DEMO_CODE_DISABLED` | 403 | Code nodes are turned off in the public demo |
| `DEMO_NODE_DISABLED` | 403 | {node} nodes are turned off in the public demo |
| `DEMO_READ_ONLY` | 403 | The public demo is read-only: you can open, edit and run workflows, but not save changes |
| `CODE_RUNTIME_OFF` | 400 | Code nodes are turned off on this server (STUDIO_ENABLE_CODE_NODES) |
| `CODE_RUNTIME_UNAVAILABLE` | 503 | Code nodes cannot run on this server: {reason} |
| `CODE_INVALID` | 400 | Code node {node}: {reason} |
| `CODE_FAILED` | 400 | Code node {node} raised {error} |
| `CODE_TIMEOUT` | 400 | Code node {node} was stopped after {seconds} s |
| `CODE_MEMORY` | 400 | Code node {node} ran out of memory (limit {limit}) |
| `CODE_RESULT_NOT_JSON` | 400 | Code node {node}: main() returned {type}, which cannot be stored as JSON |
| `CODE_TOO_LARGE` | 413 | Code node {node}: the {what} is larger than {max_kb} KB |
| `CODE_LANGUAGE_UNSUPPORTED` | 400 | Code node {node}: {language} is not available on this server |
| `CODE_WRITE_FORBIDDEN` | 403 | Your role may not add Code nodes or change their code (code.write) |
| `RUN_NOT_WAITING` | 409 | This run is not waiting for a response |
| `CHECKPOINT_NOT_FOUND` | 404 | Checkpoint not found in this run, or it cannot be forked |
| `RUN_FORK_UNSUPPORTED` | 400 | Runs of imported LangGraph graphs cannot be forked |
| `RUN_RESPONSE_INVALID` | 400 | The response must be text (max {max} characters) |
| `MCP_SERVER_DISABLED` | 403 | This workflow is not exposed as an MCP tool; turn it on under API in the editor |
| `TRIGGER_TOKEN_INVALID` | 401 | Missing, invalid or revoked workflow token |
| `TOKEN_NOT_FOUND` | 404 | Token not found |
| `SCHEDULE_NOT_FOUND` | 404 | Schedule not found |
| `SCHEDULE_CRON_INVALID` | 400 | Schedule: {reason} |
| `SCHEDULE_LIMIT` | 400 | A workflow can have at most {max} schedules |
| `CHAT_TRIGGER_NOT_FOUND` | 404 | Chat trigger not found |
| `CHAT_TRIGGER_COMMAND_TAKEN` | 409 | Another chat trigger already answers '{command}' there |
| `CHAT_TRIGGER_LIMIT` | 400 | A workflow can have at most {max} chat triggers |
| `CHAT_TRIGGER_CONFIG_INVALID` | 400 | Chat trigger: invalid {field} |
| `CHAT_TRIGGER_SCOPE_MISSING` | 400 | The Slack app lacks the scopes chat triggers need: {scopes}. Reinstall it with them |
| `CHAT_IDENTITY_UNKNOWN` | 403 | Their {kind} account is not linked to Superstep |
| `CHAT_IDENTITY_UNVERIFIED` | 403 | Their {kind} account is linked but not verified |
| `CHAT_FORBIDDEN` | 403 | They may not run this workflow |
| `CHAT_TRIGGER_OFF` | 409 | The chat trigger is off |
| `CHAT_NOT_ENABLED` | 409 | Chat is off for this workflow. Turn it on in the Chat settings |
| `CHAT_SETTINGS_INVALID` | 400 | Chat settings: invalid {field} |
| `CHAT_ACCESS_NOT_AVAILABLE` | 400 | Chat access '{access}' is not available yet |
| `CHAT_SESSION_NOT_FOUND` | 404 | Chat not found |
| `CHAT_MESSAGE_EMPTY` | 400 | Write a message first |
| `CHAT_MESSAGE_TOO_LONG` | 400 | The message is longer than {max} characters |
| `CHAT_RUN_WAITING` | 409 | Answer the question in the chat first |
| `CHAT_ANSWER_BY_REVIEWER` | 409 | A reviewer answers this step in the Approvals inbox |
| `TEST_NOT_FOUND` | 404 | Test case not found |
| `TEST_CASE_INVALID` | 400 | Test case: {reason} |
| `TEST_CASES_LIMIT` | 400 | A workflow can have at most {max} test cases |
| `TEST_SUITE_NOT_FOUND` | 404 | Test run not found |
| `TEST_SUITE_RUNNING` | 409 | The tests of this workflow are already running |
| `TEST_NOT_SUPPORTED` | 400 | Imported LangGraph workflows cannot have tests |
| `PYTHON_EXPORT_UNAVAILABLE` | 400 | Imported LangGraph workflows are Python code already: there is nothing to export |
| `TYPESCRIPT_EXPORT_UNAVAILABLE` | 400 | Imported LangGraph workflows are Python code: they cannot be exported as TypeScript |
| `EXPORT_LANGUAGE_UNSUPPORTED` | 400 | Cannot export to {language}: use one of {supported} |
| `CALLBACK_URL_INVALID` | 400 | callback_url must be a public http(s) URL |
| `VERSION_NOT_FOUND` | 404 | Workflow version not found |
| `RUN_INTERRUPTED` | 500 | The server stopped while this run was going {attempts} times, so it was not continued again |
| `RUN_EXPIRED` | 410 | This run waited too long for a response and expired |
| `RATE_LIMITED` | 429 | Too many requests, retry in {retry_after} s |
| `NOTIFICATION_NOT_FOUND` | 404 | Notification not found |
| `DELIVERY_NOT_FOUND` | 404 | Webhook delivery not found |
| `NOTIFICATION_PREFS_INVALID` | 422 | Preferences: in_app and email must be booleans, lang must be en or vi |
| `CHANNEL_KIND_UNSUPPORTED` | 400 | Unsupported approval channel: {kind} |
| `CHANNEL_CONFIG_INVALID` | 400 | Channel setting {field} is missing or invalid |
| `CHANNEL_NOT_FOUND` | 404 | Approval channel not configured |
| `CHANNEL_ADMIN_REQUIRED` | 403 | Only an admin can manage org-wide approval channels |
| `CHANNEL_PUBLIC_URL_REQUIRED` | 400 | Set STUDIO_PUBLIC_URL to the public https URL of the studio first |
| `CHANNEL_SIGNATURE_INVALID` | 401 | Invalid channel request signature |
| `CHANNEL_API_FAILED` | 502 | The {kind} API call failed: {reason} |
| `IDENTITY_INVALID` | 400 | Invalid {kind} user id |
| `IDENTITY_TAKEN` | 409 | This {kind} account is already linked to another user |
| `IDENTITY_NOT_LINKED` | 404 | Link your {kind} account first |
| `IDENTITY_CODE_INVALID` | 400 | Wrong code, {left} attempt(s) left |
| `IDENTITY_CODE_EXPIRED` | 410 | The code expired, request a new one |
| `IDENTITY_CODE_ATTEMPTS` | 429 | Too many wrong codes, request a new one |
| `APPROVAL_TOKEN_INVALID` | 400 | Invalid approval button |
| `APPROVAL_TOKEN_EXPIRED` | 410 | This approval request has expired |
| `APPROVAL_ALREADY_DECIDED` | 409 | This request was already answered |
| `APPROVAL_IDENTITY_UNKNOWN` | 403 | Link and verify your {kind} account in Superstep (Settings → My accounts) to approve |
| `APPROVAL_FORBIDDEN` | 403 | You are not allowed to approve this run |

Codes used only in WebSocket events (`RUN_*`, `NODE_FAILED`) list their nominal status for reference.


### LLM providers (TASK-0030)

`PROVIDER_*` and `MODEL_NOT_FOUND` come from `POST /api/providers/{id}/test`, `GET /api/credentials/{id}/models` and, as the `code` of a run `error` event, from LLM nodes. `PROVIDER_AUTH_FAILED` is deliberately 400 (not 401) so the UI does not treat a rejected provider key as an expired studio session. `PROVIDER_UNREACHABLE` in Docker usually means the base URL says `localhost`: use `http://host.docker.internal:<port>` (see the handbook, *LLM providers*).

`PROVIDER_EMBEDDINGS_UNSUPPORTED` and `KB_EMBEDDING_DIMENSION_MISMATCH` come from knowledge-base uploads, re-index, search and `POST /api/credentials/{id}/embeddings/test`. A knowledge base stores the dimension of its vectors (`dims`); a model that suddenly returns another size (same name, e.g. a re-pulled local model) is refused instead of mixing vectors. Changing the model or credential still re-indexes automatically.

### Send email nodes (TASK-0051)

`CREDENTIAL_SETTINGS_INVALID` comes from creating, editing or testing an SMTP credential (`details.field` names the setting). `EMAIL_HOST_BLOCKED`, `EMAIL_AUTH_FAILED` and `EMAIL_SEND_FAILED` come from its *Test connection* and, as the `code` of a run `error` event, from Send email nodes, together with the other `EMAIL_*` codes. `EMAIL_AUTH_FAILED` is 400 (not 401) for the same reason as `PROVIDER_AUTH_FAILED`. `EMAIL_RATE_LIMITED` counts recipients per workflow owner in a fixed one-hour window (`STUDIO_EMAIL_NODE_HOURLY_LIMIT`, default 100).

### Code mode of Tool nodes (TASK-0053)

The `CODE_*` codes are the `code` of a run `error` event from a Tool node in Code mode. `CODE_FAILED`, `CODE_INVALID` (raised by the code itself), `CODE_RESULT_NOT_JSON`, `CODE_TIMEOUT` and `CODE_MEMORY` events also carry `code_output` with `stdout`, `traceback` and `runtime`. The `DEMO_*` codes appear only with `STUDIO_DEMO_MODE=true` (the public demo, `docs/deploy/demo.md`). `CODE_RUNTIME_OFF` and `CODE_RUNTIME_UNAVAILABLE` mean the server cannot run code at all: the mode is off (`STUDIO_ENABLE_CODE_NODES`), Docker is not reachable, or the image (`STUDIO_CODE_IMAGE`, default `studio-code:1`) is missing. TypeScript nodes (TASK-0080) use their own image (`STUDIO_CODE_TS_IMAGE`, default `studio-code-ts:1`) or, on the subprocess runtime, the `deno` binary (`STUDIO_DENO`); a TypeScript import outside `STUDIO_CODE_TS_PACKAGES`, or one that is not in Deno's cache, is `CODE_INVALID`. The allowed entries are pinned `name@major` (default `npm:zod@3,npm:date-fns@4`) and an import must name the same major (`npm:zod@3`, `npm:zod@3.25.1` or `npm:zod@3/mini`); an unversioned `npm:zod` or another major is refused at save time with a reason that names the allowed spec (`import "npm:zod" needs a version: use "npm:zod@3"`), and an action Deno has no permission for (files, network, environment, processes) is `CODE_FAILED`.

`CODE_LANGUAGE_UNSUPPORTED` (TASK-0079) means the node's `data.language` is unknown or not in `STUDIO_CODE_LANGUAGES` on this server (`python` by default). Nodes without a `language` are Python. It is raised before anything runs, by a run and by *Test with sample state*; saving such a graph reports the same problem as a validation error.

`CODE_WRITE_FORBIDDEN` (TASK-0054) comes from saving a workflow, restoring a version, using or importing a template, and any other write that adds a Code node or changes its `code`, when the user's role lacks `code.write` (admins only by default). Running, moving, renaming or deleting a Code node, and duplicating a workflow, stay allowed. Nothing is stored when it is refused.
<!-- --8<-- [end:catalog] -->
