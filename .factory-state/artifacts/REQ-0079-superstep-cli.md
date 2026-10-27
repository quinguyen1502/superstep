# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0079
- Status: Draft. Waiting on the owner's answers to CLAR-0010.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Source: owner request in chat on 2026-10-27: "Tôi muốn thêm 1 REQ về việc build superstep cli để hỗ trợ deploy,
  install, upgrade,... và nhiều thêm nữa dựa vào bạn đề xuất". The commands beyond install, deploy and upgrade are
  the agent's proposals, and CLAR-0010 asks which of them the first version takes.

## Summary

- A `superstep` command-line tool with two jobs.
- **Run a Superstep instance**:
  - `install`: an interactive set-up on a Docker host, with generated secrets and the first admin;
  - `deploy` to a remote Docker host;
  - `upgrade`, with a backup first and a way back;
  - `backup` and `restore`;
  - `status`, `logs`, `doctor`;
  - managing admins.
- **Work with workflows from a terminal and in CI**:
  - sign in;
  - list, export and import workflows as files;
  - run a workflow and follow its trace;
  - run test suites with an exit code for CI;
  - expose workflows to MCP clients over stdio.
- The first version's scope, the packaging and the deploy targets are set by CLAR-0010.

## Problem Or Opportunity

- **Installing** takes a dozen manual steps from the docs today (`docs/deploy/README.md`, the handbook's "Deploy with
  Compose"):
  - choose the single image or the full Compose stack;
  - set `JWT_SECRET`, `STUDIO_SECRET_KEY`, `STUDIO_ADMIN_EMAILS`, `STUDIO_PUBLIC_URL` and `STUDIO_ENV=production`;
  - build the sandbox images (`studio-code`, `studio-code-ts`, `studio-sandbox`);
  - start the stack and wait for it.
  - A wrong or missing secret is the most common mistake, and losing `STUDIO_SECRET_KEY` makes stored credentials
    unreadable.
- **Upgrading** means pulling a new image and restarting. Alembic migrates at start-up and the migrations only go
  forward, so a bad upgrade cannot simply go back to the old image. There is no backup step, and the docs only say
  "back up the volume".
- **Backups** are left to the operator (`pg_dump`, copying the SQLite file and `/data/secret.key`).
- **Workflows from a terminal**: there is no way to keep workflows in Git, to run a test suite in CI, or to call a
  workflow from a shell script without writing code against the SDK.
- Comparable tools ship a CLI:
  - Dify has `docker compose` plus scripts;
  - n8n has `n8n export:workflow` and `import:workflow`;
  - Langflow has `langflow run`;
  - LangGraph has `langgraph dev`, `build` and `deploy`;
  - Flowise has `npx flowise start`.

## Scope

### In Scope

The groups below are proposals. CLAR-0010 question 2 decides which groups the first version takes.

**A. Instance lifecycle** (on the machine where Docker runs, or a remote one over SSH):

- `superstep install`:
  - checks the host (Docker and Compose versions, free ports, memory, disk);
  - asks for the topology (CLAR-0010 question 3), the public URL and the first admin's e-mail;
  - generates the secrets and writes them to an `.env` file with mode `0600`, next to a Compose file pinned to the
    current release;
  - pulls or builds the images, including the sandbox images when the topology uses them;
  - starts the stack, waits for `/api/health`, and prints the URL and the admin's first sign-in link.
  - It can run without questions (`--yes` plus flags, or an answers file) for scripts.
- `superstep status`: the version, the health of each service, the database and queue kind, the disk used by the
  volumes, and whether a newer release exists.
- `superstep start`, `stop`, `restart` and `logs [service] [--follow]`: thin wrappers over Compose for the installed
  project.
- `superstep doctor`: checks the installation and suggests fixes. It covers:
  - the secrets, and that the `STUDIO_SECRET_KEY` file is backed up;
  - `STUDIO_ENV=production`, TLS in front, `STUDIO_TRUSTED_PROXIES`;
  - the Docker socket for sandboxed Code nodes;
  - the clock;
  - outbound access to the model providers that are set.
- `superstep upgrade [--to <version>]`:
  1. shows the CHANGELOG between the running version and the target;
  2. takes a backup;
  3. pulls the new images;
  4. restarts, so Alembic migrates;
  5. waits for health;
  6. if health fails, restores the backup and the previous version (CLAR-0010 question 5).
  - `--check` only reports whether an upgrade is available.
- `superstep backup [--to <dir>]` and `superstep restore <archive>`:
  - one archive holds the database (the SQLite file, or `pg_dump` of Postgres), the secret key, the `.env` and the
    Compose file, and a manifest with the version;
  - restore refuses an archive from a newer version;
  - backups can be scheduled (CLAR-0010 question 6).
- `superstep admin create | reset-password | list`, which works when nobody can sign in.
- `superstep config get | set | list` for the installation's settings, with a restart when one needs it. Secrets are
  shown masked.
- `superstep uninstall`, which keeps the volumes unless `--purge` is given together with the instance's name typed
  back, in line with DEC-0025.

**B. Deploy** (CLAR-0010 question 4):

- `superstep deploy ssh://user@host` runs `install` or `upgrade` on a remote Docker host over SSH, with Docker's own
  `ssh://` context, so nothing besides Docker has to be installed there.
- Platform deploys (Fly.io, Render, Railway, Zeabur, Heroku) reuse the repository's existing configs (`fly.toml`,
  `render.yaml`, `railway.json`, `deploy/zeabur`, `heroku.yml`) and the platform's own CLI, if the owner takes them.

**C. Workflows from a terminal and CI**:

- `superstep login [--url]`: a browser sign-in that creates a personal access token for the CLI (CLAR-0010 question
  7). `logout`, and `whoami`.
- `superstep workflows list`, `export <id> [--format json|python|langgraph|typescript]`, and `import <file>`.
  - `superstep pull` and `push` keep a folder of workflow files in sync with the studio, so workflows can live in Git.
  - A push refuses to overwrite a workflow changed in the studio since the last pull, unless `--force` is given.
- `superstep run <workflow> [--input file|-] [--follow]`: starts a run and streams its trace as the run panel does.
  - `--json` prints the final state.
  - The exit code is 0 for `ok`, and non-zero for `error`, `waiting` and `timeout`.
- `superstep runs list | show | cancel`.
- `superstep test <workflow>|--all`: runs the test suites (REQ-0042). It prints a summary and a JUnit XML file for CI,
  and exits non-zero on a failure.
- `superstep mcp <workflow...>`: a stdio MCP server that forwards to the studio's `/mcp` endpoint (REQ-0070), so
  Claude Desktop and other clients that only start local processes can use the workflows.

**D. Common to every command**:

- `--help` on every command, with examples.
- `--json` output for scripts.
- en and vi messages, chosen from the locale.
- Shell completion for bash, zsh and fish.
- `superstep version` prints the CLI's and the server's versions, and warns when they are far apart.

**E. Server side**, where the CLI needs it:

- `GET /api/version`, or the version in `/api/health`.
- Personal access tokens, if CLAR-0010 question 7 chooses them: create, list and revoke in Settings, scoped to the
  user's rights, with only a hash stored, as for workflow tokens.
- A browser sign-in flow for the CLI.

**F. Delivery**:

- Packaging and distribution as CLAR-0010 question 1 decides, released with every Superstep tag (CLAR-0010
  question 8).
- Handbook en and vi: a "CLI" section (install, upgrade, backup, CI recipes), and the deploy pages updated to start
  from the CLI. CHANGELOG. A decision record for the packaging and the install layout.

### Out Of Scope

- Kubernetes and Helm charts, unless CLAR-0010 question 4 adds them.
- A hosted Superstep service. The vision lists "public multi-tenant SaaS" as a non-goal.
- Managing several instances as a fleet from one command.
- A terminal UI for editing workflows. The canvas stays the editor.
- Windows without WSL (CLAR-0010 question 1).

## Stakeholders Or Users

- Operators who install and upgrade Superstep on their own servers.
- Builders who keep workflows in Git and run their tests in CI.
- Developers who call workflows from scripts or local MCP clients.

## Current Context

- Deployment:
  - `docker-compose.yml`: `postgres` (pgvector 17), `redis`, `api`, `worker`, `web` (nginx), plus the `sandbox` and
    `tracing` profiles;
  - `deploy/compose/docker-compose.single.yml`: the all-in-one image with SQLite on a volume;
  - `Dockerfile`; the images `ghcr.io/quinguyen1502/superstep` and its `-sandbox`, published by `image.yml` on tags;
  - platform configs: `fly.toml`, `render.yaml`, `railway.json`, `heroku.yml`, `app.json`, `deploy/zeabur`,
    `deploy/render`.
- Docs: `docs/deploy/*`, the handbook's `operate/deploy.md` (production checklist, upgrade from v0.1.0), and
  `docs/deploy/env-vars.md` (about 35 variables).
- The server migrates with Alembic at start-up under a lock. Migrations go forward only.
- `/api/health` reports `ok`, `llm_mode`, `database`, `run_bus`, `tracing` and `import_enabled`, but not the version.
- Auth:
  - studio sessions are JWT cookies;
  - the public API and `/mcp` take per-workflow tokens (`workflow_tokens`, REQ-0004 and REQ-0070);
  - there are no personal access tokens.
- The Python SDK is `superstep` (`sdk/python`, httpx, Python 3.9+, published to PyPI by `sdk-publish.yml` on
  `sdk-py-v*` tags). The TypeScript SDK is `@superstep/sdk`.
- Workflow exports exist for Python, the LangGraph project and TypeScript (REQ-0043, REQ-0053, REQ-0047). Test suites and their
  API exist (REQ-0042).
- `dev.sh` runs a development checkout. It is not for operators.
- The Factory framework has its own `factory` CLI. It is unrelated, and the names must not clash.

## Desired Behavior

1. On a fresh Ubuntu server with Docker, an operator runs the one-line installer, then `superstep install`. They
   answer three questions: topology, URL and admin e-mail. A few minutes later they get the URL and a sign-in link.
2. A month later, `superstep status` says 0.10.0 is out. `superstep upgrade` shows what changed, backs up, upgrades
   and confirms that the instance is healthy.
3. An upgrade fails its health check. The CLI restores the backup and the previous version, and says where the
   failed upgrade's logs are.
4. A builder runs `superstep login`, then `superstep pull ./workflows`, commits the files, and adds
   `superstep test --all` to CI. A change that breaks a test fails the pipeline.
5. A developer adds `superstep mcp support-team` to Claude Desktop's config and calls the workflow as a tool.

## Business Rules

- Secrets are generated with a cryptographic random source. They are never printed except when the operator asks
  explicitly, and are written only to files with mode `0600`.
- `upgrade` and `restore` never run without a backup made by the same command or named by the operator.
- `restore` and `uninstall --purge` ask for confirmation by typing the instance's name (DEC-0025). `--yes` is needed
  to skip it in scripts.
- A CLI command uses only the rights of its token. The CLI is never a way around the studio's access rules.
- The CLI never sends telemetry.

## Constraints

- Server-side additions keep the layers of DEC-0009, the response envelope, the error catalog and en and vi.
- The CLI uses the public and studio APIs. It never reads the database directly, except for `backup`, `restore` and
  `admin` on the host, which run inside the API container with the server's own code.
- Install and upgrade work offline with images already loaded (`--images <tar>`), for air-gapped servers.
- The CLI keeps its state (`~/.superstep/cli.json`, the tokens) apart from the server's `~/.superstep/` data used by
  local runs.

## Acceptance Criteria

- On a clean Linux VM with Docker, `superstep install --yes` with flags brings up a healthy instance of the chosen
  topology. A second run detects the installation and refuses to overwrite it.
- `superstep upgrade` from the previous release to the current one succeeds with a backup. An upgrade forced to fail
  its health check restores the previous version, and the data is intact.
- `superstep backup`, then `restore` on a fresh VM, gives the same workflows, runs and credentials. Credentials
  decrypt, so the secret key travelled with the backup.
- `superstep doctor` reports a missing `STUDIO_ENV=production`, a placeholder secret, and a missing Docker socket for
  sandboxed Code nodes.
- `superstep login`, `pull`, `push`, `run --follow` and `test --all` work against a test instance. `test` exits
  non-zero on a failing case and writes JUnit XML.
- `superstep mcp` serves a workflow to an MCP client over stdio. An integration test uses the MCP SDK's client.
- Every command has `--help` and `--json`, and its messages exist in en and vi.
- CI runs the CLI's unit tests, and an install-and-upgrade smoke test on Docker, in the same way as `compose_smoke.py`.

## Edge Cases

- Ports 80, 443 or 8000 are taken. `install` says which process holds them and offers another port.
- An instance was installed by hand before the CLI existed. `superstep adopt <compose dir>` (or `install --adopt`)
  takes it over without changing its data.
- An upgrade jumps several versions. The CLI walks through them in order when a release says it must, which is the
  case for v0.1 volume names.
- The backup disk is full. The backup fails before anything is stopped.
- The token expired or was revoked. Commands say so and point to `superstep login`.
- The server is older than the CLI. Commands it does not support are refused with the server's version.

## Assumptions

- The operator has Docker with Compose v2 and SSH access to the server.
- Most installs are one Linux server, with or without a PaaS.

## Open Questions

- CLAR-0010:
  - the packaging and the platforms;
  - which command groups go in the first version;
  - the topologies;
  - the deploy targets;
  - the upgrade rollback;
  - scheduled backups;
  - authentication for workflow commands;
  - versioning.

## Related Artifacts

- `.factory-state/artifacts/CLAR-0010-superstep-cli.md`
- `.factory-state/artifacts/REQ-0008-postgres-redis-compose.md`, `.factory-state/artifacts/REQ-0042-workflow-tests.md`,
  `.factory-state/artifacts/REQ-0070-workflows-as-mcp-tools.md`, `.factory-state/artifacts/REQ-0004-api-webhook-trigger.md`
- Exports: `.factory-state/artifacts/REQ-0043-python-export.md`, `.factory-state/artifacts/REQ-0053-langgraph-project-export.md`,
  `.factory-state/artifacts/REQ-0047-typescript-export.md`
- `docs/deploy/README.md`, `docs/deploy/self-hosted.md`, `docs/deploy/env-vars.md`,
  `handbook/docs/en/operate/deploy.md`
- `docker-compose.yml`, `deploy/compose/docker-compose.single.yml`, `Dockerfile`, `.github/workflows/image.yml`,
  `.github/workflows/sdk-publish.yml`
- `sdk/python` (the `superstep` package)
- `.factory-state/decisions/DEC-0025-ui-only-delete-confirmation.md` (typed-name confirmation), `docs/backend-architecture.md`
