# Decision Record

## Metadata

- Project: superstep
- Decision ID: DEC-0068
- Status: Accepted. The owner answered CLAR-0010 on 2026-10-27 ("Làm theo đề xuất"). This record is the install layout the phase 1 tasks implement.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Related Requirements: REQ-0079 (CLAR-0010)
- Related Architecture:
  - DEC-0009 (layers, for the admin process and the health field)
  - DEC-0010 (the health response stays on the shared envelope)
  - DEC-0025 (typed-name confirmation, applied here to the CLI prompt)
  - DEC-0033 (task branches from `develop`)
- Related Tasks: TASK-0149, TASK-0150, TASK-0151, TASK-0152, TASK-0153, TASK-0154, TASK-0155, TASK-0156

## Context

- REQ-0079 phase 1 is the instance commands, the version field, and delivery. Phase 2 (personal access tokens, browser sign-in, pull and push, run, test, MCP over stdio) is out of this record's tasks.
- The PyPI package `superstep` is the SDK in `sdk/python` (httpx, Python >= 3.9, version `0.1.0` in `src/superstep/_version.py`). It is published by `.github/workflows/sdk-publish.yml` on `sdk-py-v*` tags. The server version is `0.9.0` in `backend/pyproject.toml`. There is no console script today.
- `GET /api/health` is public. The app's default response class wraps it in the envelope, so clients read `data` (`backend/tests/test_run_bus.py`). The payload has `ok`, `llm_mode`, `database`, `run_bus`, `run_bus_ok`, `tracing` and `import_enabled`, and no version (`backend/app/api/routes/meta.py`).
- Published images today (`.github/workflows/image.yml`) are `ghcr.io/quinguyen1502/superstep` (root `Dockerfile`, all-in-one) and `ghcr.io/quinguyen1502/superstep-sandbox`. The full Compose file builds `backend/Dockerfile` and `frontend/Dockerfile` from a checkout. Those two images are not published.
- The full Compose project pins the v0.1 volume names `langgraph-studio_pgdata`, `_redisdata` and `_apidata` (`docker-compose.yml`, handbook "Upgrade from v0.1.0").
- A first admin is created at start-up from `STUDIO_ADMIN_EMAILS`. A generated password is logged once (`backend/app/services/seed.py`). Production refuses the placeholder `JWT_SECRET` `dev-secret-change-me`.
- Local runs already use `~/.superstep/` for the secret key and imports. The CLI must not write over those files.
- No separate design artifact. REQ-0079 already fixes the prompts, the flags, the languages and the confirmation. The designer step of the large-task workflow is skipped for that reason.

## Decision

1. **Packaging and version.**
   - The command lives in the SDK tree: `sdk/python/src/superstep/cli/`. The console script is `superstep = superstep.cli:main`.
   - The extra `cli` is declared now. Phase 1 adds no third-party dependency: the command uses the standard library and httpx, which the SDK already depends on. Phase 2 adds the MCP SDK to that extra. `pipx install 'superstep[cli]'` and `uv tool install 'superstep[cli]'` are the install commands. The script is installed with the base package as well, because a console script cannot be gated by an extra.
   - Python stays `>=3.9`, the SDK's floor. The CLI does not use `tomllib`.
   - The CLI version and the server version are the same number on a `v*` release. Until TASK-0156, `sdk/python` may stay at `0.1.0` while the server stays at `0.9.0`. Tests inject both versions. The release workflow, not a day-to-day test, checks that the tag, `_version.py` and `backend/pyproject.toml` match.
   - `scripts/install.sh` is the one-line installer (TASK-0156). It installs uv when `python` is missing, then installs the extra. It refuses native Windows and tells the operator to use WSL.
2. **Command program.**
   - `argparse` subparsers. No Click and no Typer.
   - Every command accepts `--help` (with an example) and `--json`.
   - Human text and prompts go to stderr. `--json` writes one object to stdout and nothing else. Exit 0 on success, non-zero on failure. A JSON failure is `{"ok": false, "error": {"code", "message"}}`. These codes belong to the CLI, not to `core/errors.py`.
   - Messages come from `superstep/cli/locales/en.json` and `vi.json`, with the same keys. The language is `--lang`, then `lang` in `~/.superstep/cli.json`, then the `vi` prefix of `LANG` or `LC_MESSAGES`, otherwise English.
   - `superstep completion bash|zsh|fish` prints a completion script generated from the parser.
   - `superstep version` prints the CLI version and, when a base URL is known, the server version. It warns, and still exits 0, when `data.version` is missing or the `major.minor` differs. It never prints a secret.
3. **Instance directory.**
   - One instance is a directory `~/.superstep/instances/<name>/`, default name `superstep`. `--dir` overrides the directory. The directory is created mode `0700`.
   - Files: `compose.yml`, `.env` mode `0600`, `instance.json` mode `0600`.
   - `instance.json` holds `name`, `topology` (`single` or `full`), `sandbox` (bool), `version`, `public_url`, `dir`, `remote` (`null` or `ssh://user@host`), `created` (UTC), and `volumes` (logical name to Docker volume name).
   - `~/.superstep/cli.json` holds the CLI's own preferences (`lang`, `current`). It is not server data. The CLI never writes `~/.superstep/secret.key` or the import directory.
   - A second `install` into an existing `instance.json` refuses, unless the command is `adopt`.
4. **Topologies and images.**
   - `single` is the default. One service, image `ghcr.io/quinguyen1502/superstep:<version>`, a named volume at `/data`, host port `${PORT:-8000}`. Code nodes use the image's subprocess runtime. No sandbox on this topology.
   - `full` is Postgres `pgvector/pgvector:pg17`, Redis `redis:7-alpine`, `api` and `worker` from `ghcr.io/quinguyen1502/superstep-api:<version>` (`backend/Dockerfile`; the worker command is `python -m app.worker`), and `web` from `ghcr.io/quinguyen1502/superstep-web:<version>` (`frontend/Dockerfile`) on host port `${WEB_PORT:-8080}`. `--sandbox` adds `ghcr.io/quinguyen1502/superstep-sandbox:<version>`.
   - The generated compose file uses `image:` pinned to the version. It has no `build:` path. A new full install uses volume names `<name>_pgdata`, `<name>_redisdata` and `<name>_apidata`. It does not reuse the `langgraph-studio_*` names.
   - TASK-0156 publishes `superstep-api` and `superstep-web` from the existing Dockerfiles. The other two images are already published. Until those images exist, install tests load local tags with `--images`.
   - `STUDIO_ENV=production` is always set. The minimum `.env` is `JWT_SECRET`, `STUDIO_SECRET_KEY`, `STUDIO_ADMIN_EMAILS`, `STUDIO_ADMIN_PASSWORD`, `STUDIO_PUBLIC_URL`, and for `full` also `POSTGRES_PASSWORD`. The Compose file builds `DATABASE_URL` and `REDIS_URL` from the service names.
5. **Docker and SSH.**
   - The CLI shells out to `docker` and `docker compose`. The wrapper is `superstep.cli.docker`. Tests use a fake. There is no Docker SDK dependency.
   - `install` requires the Docker engine and Compose v2. It reports memory and free disk and warns below 1 GiB of memory or 2 GiB of free disk. Those warnings do not block. A taken port is named (the process, when the host says so) and another port is offered. With `--yes`, `--port` is required when the default is taken.
   - `--images <tar>` runs `docker load` and does not pull.
   - `superstep deploy ssh://user@host` keeps the instance directory on the Docker host, at the same path under that host's home. The operator's machine does not need a copy except as a cache. Engine calls use Docker's SSH transport (`DOCKER_HOST=ssh://user@host`). The remote host needs Docker with Compose v2 and nothing else: no Python and no CLI. A scheduled backup is a shell script plus a systemd user timer, or cron when systemd is missing, installed over that SSH. The script calls `docker` only.
   - `adopt` takes an existing compose directory, writes `instance.json`, and does not recreate volumes or rotate secrets.
6. **Secrets and confirmation.**
   - `JWT_SECRET`, `STUDIO_SECRET_KEY` and `POSTGRES_PASSWORD` come from `secrets.token_hex(32)`. They are written only into `.env`. They are never printed. `config get` masks any value whose name contains `SECRET`, `PASSWORD`, `TOKEN` or `KEY`. `--show-secrets` prints them, including under `--json`.
   - The one-time admin password is the exception already used at start-up: `install` prints it once on the terminal and, with `--json`, once as `admin_password`. It is stored in `.env` so a retry of the first start keeps it. It is not written into `instance.json`.
   - `restore` and `uninstall --purge` ask the operator to type the instance name. `--yes` skips the prompt only when `--name` equals that name. `--yes` alone is refused. `uninstall` without `--purge` runs `docker compose down` and keeps the volumes.
7. **Health version.**
   - `GET /api/health` gains `version`, the `superstep-backend` package version. The body stays the envelope. No new route and no auth change.
8. **Backup archive.**
   - One `superstep-backup-<name>-<utc>.tar.gz`, mode `0600`. Members: `manifest.json` (format `1`, server version, topology, instance name, created), the database (`pg_dump` custom format, or the SQLite file via the engine's online backup), `secret.key` or the `STUDIO_SECRET_KEY` value, `.env` and `compose.yml`.
   - The CLI checks free space against the estimate first. A short disk fails before any container is stopped. The dump runs against the live database. Restore refuses a manifest format it does not know, or an archive whose server version is newer than the CLI.
   - `--schedule <period> --keep <n>` installs the timer from decision 5 and deletes archives beyond `<n>`. The period is `daily` or `weekly`.
9. **Upgrade and rollback.**
   - `upgrade` reads the bundled `CHANGELOG.md` for the range, runs `backup`, pulls the pinned images (or loads `--images`), restarts so Alembic migrates, and waits for `/api/health`. `--check` reports without changing anything. `--to <version>` selects the tag. The default target is the CLI's own version.
   - When the health check fails, the CLI restores that backup, starts the previous image tag, and writes the failed upgrade's logs to `<dir>/upgrade-failed-<utc>.log`.
   - The only ordered gate in phase 1 is v0.1. An instance whose volumes are `langgraph-studio_pgdata`, `_redisdata` or `_apidata`, or whose Compose project is `langgraph-studio`, is stopped without `-v` and brought up with those external volume names. Later gates are rows in a table in the CLI, empty besides this one. Schema steps stay Alembic's job.
10. **Admin process.**
    - `superstep admin create|reset-password|list` runs `python -m app.admin_cmd` inside the API container (`docker compose exec`). No HTTP route. `backend/app/admin_cmd.py` follows `app/worker.py`: it opens the database through the existing deps and calls a service. The service hashes passwords with `core.security` and uses `UserRepository`. A generated password is printed once and is not stored in the CLI. `list` prints e-mail and role, never a hash.
11. **Phase 1 does not build** personal access tokens, browser sign-in, workflow pull or push, `run`, `test`, MCP over stdio, Kubernetes, or deploy to Fly.io, Render, Railway, Zeabur or Heroku.

## Rationale

The owner chose a Python extra on the package that already exists, the same version as the server, SSH only, and automatic rollback. Generating a compose file from pinned images is what makes `install` work on a host that has Docker and no git checkout. Publishing the API and web images is the missing piece of the full topology, not a new product. Keeping admin off HTTP is what makes it work when nobody can sign in, and it stays inside DEC-0009.

## Alternatives Considered

- Option: A separate PyPI distribution for the CLI
  - Benefits: The SDK version can stay `0.1.0`.
  - Tradeoffs: Breaks the owner's "cli extra of the superstep package" choice, and adds a second name.
  - Reason Not Chosen: CLAR-0010 question 1.
- Option: Build the full stack from a git checkout on the server
  - Benefits: No new images.
  - Tradeoffs: The server needs git, the source, and a compiler. Air-gapped `--images` cannot build that.
  - Reason Not Chosen: The requirement is a Docker host and a pinned release.
- Option: Click or Typer
  - Benefits: Less argparse code.
  - Tradeoffs: A dependency the phase 1 extra was meant to avoid.
  - Reason Not Chosen: The standard library covers help, subcommands and completion.
- Option: Ask before rolling an upgrade back
  - Benefits: An operator can inspect the failure first.
  - Tradeoffs: The instance stays down until someone answers.
  - Reason Not Chosen: CLAR-0010 question 5.

## Impacts

- SDK users who `pip install superstep` gain a `superstep` command. It does not import the server.
- TASK-0156 publishes two images and publishes the Python package on `v*` tags. `sdk-py-v*` stays valid, and its version must be greater than the latest `v*` release once those tags share the package.
- `~/.superstep/instances/` is new. Existing `~/.superstep/` server files stay where they are.
- Phase 2 tasks, when planned, add the token store under `~/.superstep/cli.json` and the `mcp` dependency on the `cli` extra. They do not get a second package.

## Risks

- A remote `DOCKER_HOST=ssh://` uses the remote daemon's volumes. A scheduled backup that runs on the wrong machine would copy empty data. The timer is installed on the Docker host (decision 5), and the script checks the volume names in `instance.json`.
- Rolling back an Alembic migration is impossible. Rollback restores the backup and the previous image (decision 9). A backup that omitted `secret.key` would restore a database whose credentials cannot be read. The archive must contain the key, and restore checks that member.
- Publishing `superstep==<server version>` jumps the package from `0.1.0`. The release notes in TASK-0156 say so.

## Approval

- Approved By: Thái Quí Nguyễn, by the CLAR-0010 answers on 2026-10-27
- Approved On: 2026-10-27
- Scope And Limits: Phase 1 of REQ-0079. The layout in decisions 3 to 10 is the planning record for those answers. Phase 2 is not approved for implementation by this record.

## Review Or Revisit Trigger

- A phase 2 task needs a different token path or a CLI dependency the extra cannot carry.
- A release has to step through more than the v0.1 volume gate.
- The full-stack images cannot be published from `backend/Dockerfile` and `frontend/Dockerfile` without a change to those Dockerfiles.
