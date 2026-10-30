# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0071
- Status: Accepted. The owner confirmed the task set on 2026-10-30. TASK-0167 is merged (PR #214, merge `4d0ed17`).
- Owner: Thái Quí Nguyễn
- Created: 2026-10-30
- Updated: 2026-10-30
- Related Requirements: REQ-0079 (CLAR-0010, phase 2)
- Related Architecture:
  - DEC-0068 (phase 1 layout; this record keeps it and replaces one sentence)
  - DEC-0061 (`/mcp` stays a workflow-token server; this record adds a PAT path)
  - DEC-0009 (layers)
  - DEC-0010 (envelope, error catalog, en and vi)
  - DEC-0025 (typed-name revoke, UI only)
  - DEC-0008 (`docs/ui-conventions.md`)
  - DEC-0033 (task branches from `develop`)
- Related Tasks: TASK-0167, TASK-0168, TASK-0169, TASK-0170, TASK-0171, TASK-0172

## Context

- REQ-0079 phase 1 is merged (TASK-0149 to TASK-0156). Phase 2 is group C plus the tokens and the browser sign-in in group E. CLAR-0010 already chose personal access tokens, a browser sign-in, and `SUPERSTEP_TOKEN` for CI.
- Studio auth is a JWT (`AuthService.current`). Bearer wins over the session cookie. There is no personal access token table.
- Workflow files already round-trip through `POST /api/workflows` (`WorkflowIn` allows extra keys; `id`, `access`, `mine` and `owner_email` are response-only). `GET /api/workflows` returns `updated`. `GET /api/workflows/{id}` does not return `updated` or the latest version number. A save bumps `updated` always and bumps the version only when the stored JSON changes.
- Code export (`/export/python`, `/export/typescript`, and the LangGraph project zip) is one-way. Nothing imports Python or TypeScript back into a graph.
- The run panel starts a run on `/ws/run` and the server cancels that run when the socket closes. `GET /api/runs/{id}` returns the events saved so far. There is no user-level REST start.
- `/mcp` accepts only a workflow token and one workflow (DEC-0061). A PAT cannot call it today.
- The CLI package floor is Python >= 3.9 (DEC-0068). `mcp` 1.12 requires Python >= 3.10, and current MCP docs require 3.11. The SDK CI matrix still runs 3.9. The CLI unit job is Python 3.12 (`.github/workflows/cli.yml`).
- DEC-0068 decision 1 said phase 2 would add the MCP SDK to the `cli` extra. That sentence cannot be implemented without dropping Python 3.9 for every CLI install.
- No separate design artifact. The screens below are the ones REQ-0079 already names. The designer step is skipped for that reason.

## Decision

1. **Who the workflow commands are.**
   - `login`, `logout`, `whoami`, `workflows`, `pull`, `push`, `run`, `runs`, `test` and `mcp` use a personal access token. They do not read `instance.json` and they do not need Docker.
   - The token is read from `SUPERSTEP_TOKEN`. The base URL is read from `SUPERSTEP_URL`, then from `url` in `~/.superstep/cli.json`. The environment wins over the file.
   - `login` writes `url`, `token` and `account` (the e-mail from `GET /api/me`) into `~/.superstep/cli.json` and sets that file to mode `0600`. It leaves `lang` and `current` in place. It never prints the token. `logout` removes `token` and `account` from the file and does not revoke the server token.
   - A missing token, or a server `AUTH_TOKEN_INVALID` / `AUTH_TOKEN_EXPIRED` / `AUTH_ACCOUNT_DISABLED`, exits non-zero and the message names `superstep login`. A 404 on a phase 2 route prints the server version from `/api/health` and refuses the command (`SERVER_TOO_OLD`).

2. **Personal access tokens.**
   - Table `personal_access_tokens`: `id`, `user_id`, `name`, `token_hash` (SHA-256, unique), `prefix` (first 10 characters), `created`, `last_used`, `revoked`. The next Alembic revision after `0042_chat_ratings`. Only the hash is stored.
   - The secret is `pat_` plus `secrets.token_urlsafe(24)`. It is returned once, on create.
   - Active names are unique per user. A duplicate active name is `PAT_NAME_TAKEN`. Revoked rows do not block the name.
   - `AuthService.current` treats a Bearer or cookie value that starts with `pat_` as a PAT: hash lookup, not revoked, user still active. Anything else stays a JWT, including an unknown `pat_` (`AUTH_TOKEN_INVALID`). `last_used` is set on a successful PAT check. Password-change invalidation does not apply to PATs; revoking them is separate.
   - `ws_user` uses the same check, so `/ws/run?token=pat_…` is the signed-in user.
   - Routes, all on the envelope, caller is the token's user: `GET /api/me/tokens`, `POST /api/me/tokens` `{name}` → `{id, name, prefix, token}`, `DELETE /api/me/tokens/{id}`. List rows have no secret. Delete is `PAT_NOT_FOUND` when the id is missing or belongs to someone else.
   - A PAT has the same rights as that user. It is not a workflow token and it is not an extra scope list.

3. **Browser sign-in.**
   - `POST /api/auth/cli/devices` is public. Body `{name}` optional. Response `{device_code, user_code, verification_uri, expires_in, interval}`. `device_code` is a long secret. `user_code` is short and is what the page shows. Both are stored only as hashes. The row expires in 10 minutes. `verification_uri` is `{STUDIO_PUBLIC_URL}/cli/authorize?code={user_code}` when the public URL is set, otherwise a path the CLI joins to `--url`.
   - `GET /api/auth/cli/devices/{device_code}` is public. `pending` until the user acts. `approved` returns the new PAT secret once and then forgets it. `denied` and `expired` are errors `CLI_DEVICE_DENIED` and `CLI_DEVICE_EXPIRED`. An unknown code is `CLI_DEVICE_INVALID`.
   - The page `/cli/authorize` requires the studio session. A signed-out visitor goes to `/login?next=` using the existing `safeNext`. The page shows the account e-mail, the user code, and the token name, and it does nothing until the user presses Approve or Deny. Approve calls `POST /api/auth/cli/devices/approve` `{user_code, name}` with the session cookie. Deny calls `POST /api/auth/cli/devices/deny` `{user_code}`.
   - Settings gains a section `tokens` (`/settings/tokens`) for every signed-in user: create (name, secret shown once), list (name, prefix, created, last used), revoke. Revoke uses `ConfirmDeleteDialog` / `useConfirmDelete` and the token's name. The API stays a plain DELETE. Strings live in `locales/en.json` and `locales/vi.json`. shadcn components and theme tokens only.
   - `superstep login [--url] [--name] [--no-browser]` creates a device, prints the URL and the user code on stderr, opens the browser unless `--no-browser` is set, and polls until the terminal state. `--url` is required when no URL is stored and `SUPERSTEP_URL` is unset.

4. **Workflow files.**
   - `workflows list` is `GET /api/workflows`.
   - A workflow file is the `GET /api/workflows/{id}` body without `access`, `mine`, `owner_email`, `version` or `updated`. `GET` and list gain `version` (the latest version number, or 0 when there is no version row) and `GET` gains `updated`. Those two fields are how the CLI detects a change; they are not written back into the graph.
   - `pull <dir>` writes `<dir>/<id>.json` and `<dir>/.superstep/lock.json`. The lock is `{"format": 1, "url": "<base>", "workflows": {"<id>": {"name": "<name>", "version": <n>}}}`. Pull does not delete a local file that the server no longer has.
   - `push <dir>` refuses, and writes nothing, when the lock URL differs from the current server (`WRONG_SERVER`) or when any existing workflow's server version differs from the lock (`WORKFLOW_CHANGED`). A file with an id the server does not have is created. A file with no id is created and the new id is written back. `--force` overrides both refusals and then rewrites the lock from the server. Push does not delete a remote workflow that has no local file.
   - `workflows export <id-or-name> --format json|python|typescript|langgraph` writes one file. `json` is the pull file. `python` and `typescript` are the existing single-file exports. `langgraph` is the existing Python LangGraph project zip (`/export/python/project`).
   - `workflows import <file>` accepts only a workflow JSON file and `POST`s it. A `.py`, `.ts` or `.zip` is `NOT_A_WORKFLOW`.
   - An id or an exact name selects a workflow. Two workflows with that name are `AMBIGUOUS` and the message asks for the id.

5. **Run.**
   - `run <workflow> [--input <file|->] [--follow] [--timeout <seconds>]` opens `/ws/run?token=<pat>` and sends `{workflow_id, input}` as the run panel does. The socket stays open until the run finishes, because closing it cancels the run. Default timeout is 300 seconds; on timeout the CLI sends `{"type": "cancel"}` and exits 3.
   - `--follow` prints one stderr line per trace event that names a node or is `run_started`, `run_finished`, `run_waiting` or `error`. Without `--follow` those lines are not printed.
   - `--json` prints one final object on stdout and nothing else: `{ok, run_id, status, final_state}`. Without `--json`, stdout is empty.
   - Exit codes: 0 `ok` or `paused`, 1 `error`, 2 `waiting`, 3 `timeout`, 4 `cancelled`. A waiting run prints the prompt on stderr and does not answer it.
   - `runs list` is `GET /api/runs/pending`. `runs list --workflow <id-or-name>` is `GET /api/workflows/{id}/runs`. `runs show <run_id>` is `GET /api/runs/{id}`. `runs cancel <run_id>` is `POST /api/runs/{id}/cancel`.
   - The `cli` extra gains `websockets`, pinned to a release whose `Requires-Python` still includes 3.9. No other phase 2 dependency.

6. **Test.**
   - `test <workflow> [--mock] [--junit <path>]` and `test --all` use the existing suite routes. The CLI starts `POST /api/workflows/{id}/tests/run` (body `{"mock": true}` only when `--mock` is set), polls `GET /api/workflows/{id}/tests/runs/{sid}` until `status` is not `running`, and prints a one-line summary per case on stderr.
   - `--all` does that for every visible workflow that has at least one test, and skips the others with a stderr line. If no suite ran, the exit is non-zero (`NO_TESTS`).
   - JUnit XML is always written. The default path is `./superstep-junit.xml`. One `testsuite` per workflow, one `testcase` per result, a `failure` element when the case failed. Exit 0 only when every suite ended `done` with `failed == 0`. A failed, cancelled or errored suite is exit 1.

7. **MCP over stdio.**
   - `mcp <workflow...>` speaks MCP on stdin/stdout with the standard library only: `initialize`, `notifications/initialized`, `ping`, `tools/list` and `tools/call`. Any other method is a JSON-RPC method-not-found error. Logging stays on stderr. stdout is the protocol.
   - Each call is forwarded with httpx to `POST {url}/mcp`, `Authorization: Bearer <pat>` and `X-Superstep-Workflow: <id>`. The CLI does not create a workflow token.
   - `/mcp` keeps the workflow-token behaviour from DEC-0061. In addition, a `pat_` bearer plus that header is accepted when the user can open the workflow and `mcp_enabled` is true. Otherwise the existing 401 `TRIGGER_TOKEN_INVALID` or 403 `MCP_SERVER_DISABLED`. The rate-limit key is `pat:{token id}:{workflow id}` on the same window as workflow tokens. The run owner is the user and the source stays `api`. Tool list and tool call go through `WorkflowMcpService` without an MCP import in the service.
   - Several workflows are one process. `tools/list` merges them. A second tool with the same name gets `_<first 6 of the workflow id>` appended. A named workflow with MCP off is `MCP_DISABLED` and the process does not start.
   - The integration test uses the MCP Python SDK client (`mcp>=1.12,<2`) against this process and a test server. `mcp` is not a package dependency. The test skips when `mcp` cannot be imported, so the Python 3.9 SDK job stays green. `.github/workflows/cli.yml` installs `mcp>=1.12,<2` and sets `SUPERSTEP_MCP_TEST=1`. With that variable set, a missing `mcp` import fails the test.

8. **Delivery left as it is.**
   - No new PyPI version and no new image. TASK-0172 documents the commands in the handbook that TASK-0156 already published. The next `v*` tag ships the code.
   - The `cli` extra stays installable on Python 3.9. DEC-0068's sentence that put the MCP SDK on that extra is withdrawn.

## Rationale

The owner already chose PATs and a browser sign-in that never sees the password. A device code matches that: the CLI holds a secret, the browser holds the session, and CI uses a token made in Settings. Version numbers match "changed since the last pull" better than `updated`, because a no-op write bumps the clock. Keeping the socket open is what makes `run` the same run as the panel. Leaving `mcp` out of the extra is what keeps `pip install superstep[cli]` working on Python 3.9.

## Alternatives Considered

- Option: Put `mcp` on the `cli` extra, as DEC-0068 suggested
  - Benefits: The bridge could call the SDK instead of speaking JSON-RPC.
  - Tradeoffs: `mcp` 1.12 does not install on Python 3.9, so login and pull would fail to install there too.
  - Reason Not Chosen: DEC-0068 decision 1 fixes the floor at Python >= 3.9.
- Option: Mint a workflow token inside `superstep mcp` and forward that
  - Benefits: `/mcp` would not grow a second auth path.
  - Tradeoffs: A crashed CLI leaves a live workflow token in the user's list.
  - Reason Not Chosen: The PAT plus one header is revoked with the PAT and creates no second secret.
- Option: Start `run` with a new REST route and poll `GET /api/runs/{id}`
  - Benefits: No websocket dependency.
  - Tradeoffs: Studio runs are tied to the socket; a second start path would not be the run panel's path.
  - Reason Not Chosen: REQ-0079 asks for the same trace the panel shows.

## Impacts

- `~/.superstep/cli.json` may now hold a secret. Login forces mode `0600`.
- Bearer auth accepts `pat_` as well as a JWT. Cookie sessions are unchanged.
- `/mcp` accepts a PAT only together with `X-Superstep-Workflow`. Workflow tokens are unchanged.
- `GET /api/workflows` and `GET /api/workflows/{id}` gain `version`. The single-workflow GET also gains `updated`.
- The `cli` extra depends on `websockets`. The base package does not.

## Risks

- A user who approves a device code they did not request grants that CLI a PAT. The page requires a button and shows the account and the code; it does not approve on open.
- `push --force` overwrites studio edits since the last pull. The default refuses.
- A PAT on the query string of `/ws/run` can land in a proxy log. The CLI sends it only on that socket and never prints the URL.

## Approval

- Approved By: Thái Quí Nguyễn, by confirming the task set on 2026-10-30
- Approved On: 2026-10-30
- Scope And Limits: REQ-0079 phase 2 only. Phase 1 behaviour stays as DEC-0068, except the withdrawn MCP-extra sentence.

## Review Or Revisit Trigger

- The owner wants `push` to delete remote workflows, or `run` to answer a Human node.
- A `websockets` release drops Python 3.9 and no older pin remains.
- `/mcp` cannot accept a PAT without breaking a workflow-token client.
