# CLI

`superstep` installs, upgrades and backs up one instance on a machine that has
Docker and Compose v2. The package version is the server version. On the `0.1.0`
line the Python package was the SDK only; a `v*` release moves that package to
the server version. Sign-in, `pull`, `push`, `run`, `test` and `mcp` are in
the sections below. Those commands use a personal access token, not Docker.

## Install

The one-line installer is `scripts/install.sh`. It refuses native Windows and
tells you to use WSL. When `uv` is missing it installs uv (that step does not
need Python), then runs `uv tool install 'superstep[cli]==<version>'`.

```bash
curl -fsSL https://raw.githubusercontent.com/quinguyen1502/superstep/develop/scripts/install.sh | sh
superstep install
```

The package also installs `sstep`, a short alias that runs the same command:
`sstep status` is `superstep status`.

`superstep install` asks for the topology (`single` or `full`), the public URL
and the admin e-mail. `--yes` with those flags skips the questions. The
all-in-one image is `ghcr.io/quinguyen1502/superstep`. The full stack uses
`superstep-api` and `superstep-web`. A second install into an existing instance
refuses to overwrite it.

It also asks where chat attachments are stored: `db` (in the database, the
default) or `fs` (a folder on the data volume) on a single host, and also `s3`
(an S3-compatible bucket) for the full stack. With `--yes`, pass
`--attachment-storage db|fs|s3`; for `s3` add `--s3-bucket` and, as needed,
`--s3-endpoint`, `--s3-region`, `--s3-prefix`, `--s3-path-style` and
`--s3-access-key-id`. The secret key is never a flag: it is read from
`--s3-secret-stdin`, from `SUPERSTEP_S3_SECRET_ACCESS_KEY`, or from a hidden
prompt, and is written only to `.env` (mode 600). `superstep deploy` takes the
same flags. `superstep doctor` shows the backend and whether it works, with
the server's short reason when it does not, never a key. See
[Chat: Attachments](../run/chat.md#attachments).

Pin a release by checking out that tag before curling the script, or set
`SUPERSTEP_VERSION`.

## Upgrade

```bash
superstep upgrade --check
superstep upgrade
```

The command backs up, pulls the images for its own version (or loads `--images`),
restarts, and waits for `/api/health`. A failed health check restores that
backup and the previous image tag. The log is `upgrade-failed-<utc>.log` in the
instance directory. Schema migrations are Alembic's and are not reversed.

## Backup

```bash
superstep backup
superstep restore <archive>
superstep backup --schedule daily --keep 7
```

`restore` asks you to type the instance name. `--yes` skips that only when
`--name` is the same name. The archive carries the database, `.env`,
`compose.yml` and the secret key, so a stored credential still decrypts after a
restore onto a new directory.

Chat attachments follow their storage backend (see
[Chat: Attachments](../run/chat.md#attachments)):

| Backend | In the archive |
| --- | --- |
| `db` | Inside the database dump. |
| `fs` | Always, as `attachments.tar`. |
| `s3` | Only with `superstep backup --include-attachments`. Otherwise the manifest records the bucket and prefix, and the command reminds you to back the bucket up on its own. Scheduled backups (`--schedule`) never copy the bucket's objects; their manifest records the bucket and prefix too. |

`restore` refuses an archive whose attachment backend differs from the
instance's `STUDIO_ATTACHMENT_STORAGE`. `--force` restores anyway and keeps the
instance's own `STUDIO_ATTACHMENT_*` settings; the files go back to the backend
their rows name, and `superstep attachments migrate` then moves them.

## Attachment storage

```bash
superstep attachments migrate --to fs --dry-run
superstep attachments migrate --to fs
```

`migrate` moves chat attachment files to `db`, `fs` or `s3`. Each file is
copied, read back and checked (size and SHA-256), then its record is switched and
the old copy deleted. A file that fails stays where it was and is listed; the
exit code is then 1. An interrupted run leaves every file readable, and running
the command again continues; when nothing is left it does nothing. `--batch N`
sets how many files are read per batch (default 100). Set
`STUDIO_ATTACHMENT_STORAGE` to the same backend so new files go there too.
Files on the same backend but in an older folder, bucket or prefix are moved
as well, so `--to fs` after changing `STUDIO_ATTACHMENT_FS_PATH` (or `--to s3`
after changing the bucket or prefix) gathers them in the new place.
Admins can do the same over the API with `GET /api/admin/attachments` and
`POST /api/admin/attachments/migrate`.

## Sign in

Workflow commands do not read `instance.json`.

```bash
superstep login --url http://localhost:8000
superstep whoami
superstep logout
```

`login` prints a URL and a code, and opens the browser. On `/cli/authorize`,
while you are signed in to the studio, type the code from your terminal, then
approve or deny. Nothing is sent until you press a button. Approve only a
sign-in you started yourself just now: never type a code someone sent you. If a token with the approved name was
created in the meantime, the new token gets a free name such as `laptop (2)`. The command writes `url`, `token` and `account` to
`~/.superstep/cli.json` and sets that file to mode `0600`. It does not print
the token. `logout` removes `token` and `account` from that file. It does not
revoke the token. Revoke it in Settings, under Tokens (`/settings/tokens`).

For a script or CI, create a token in Settings and export the two variables.
The environment wins over the file. Do not commit the token. The token saved
by `login` is only sent to the server it came from: with `--url` or
`SUPERSTEP_URL` naming another server, log in there or set `SUPERSTEP_TOKEN`.

```bash
export SUPERSTEP_URL=http://localhost:8000
export SUPERSTEP_TOKEN
```

## Workflows in Git

```bash
superstep pull ./workflows
superstep push ./workflows
superstep push ./workflows --force
```

`pull` writes one `<id>.json` per visible workflow and `.superstep/lock.json`.
It does not delete a local file the server no longer has. `push` updates the
studio. If a workflow changed in the studio after the pull, `push` exits
non-zero and writes nothing. `--force` overwrites that edit. A lock from a
different server is refused the same way, unless `--force` is set. `push` does
not delete a remote workflow that has no local file.

```bash
superstep workflows list
superstep workflows export demo --format json
superstep workflows import ./demo.json
```

`import` accepts workflow JSON. A `.py`, `.ts` or `.zip` file is refused and
the server is not called.

## Run

```bash
superstep run inbox --input sample.json --follow
superstep runs list
superstep runs show RUN_ID
superstep runs cancel RUN_ID
```

`run` opens the same socket as the run panel and keeps it open until the run
ends. Exit 0 is `ok` or `paused`. Exit 1 is `error`. Exit 2 is `waiting`: the
prompt is printed and the CLI does not answer it. Exit 3 is a timeout. The
default is 300 seconds, then the CLI sends cancel. Exit 4 is `cancelled`.

## Tests in CI

Install the CLI, export `SUPERSTEP_URL` and `SUPERSTEP_TOKEN`, then run the
suite. `--mock` runs LLM nodes offline. The JUnit file is
`superstep-junit.xml` unless `--junit` names another path. The process exits 1
when a case fails or a suite is cancelled or errors.

```bash
pip install 'superstep[cli]'
export SUPERSTEP_URL=http://localhost:8000
export SUPERSTEP_TOKEN
superstep test --all --mock --junit superstep-junit.xml
```

## MCP

`superstep mcp` speaks MCP on standard input and output. Run `superstep login`
first, or set `SUPERSTEP_URL` and `SUPERSTEP_TOKEN`. Turn MCP on for the
workflow in the studio. The command does not create a workflow token and does
not put a token in the client config.

```json
{
  "mcpServers": {
    "superstep": {
      "command": "superstep",
      "args": ["mcp", "Support"]
    }
  }
}
```

Replace `Support` with the workflow name. Several names are one process.

## CI smoke test

`.github/workflows/cli.yml` runs the Python package tests on a pull request.
It does not publish. `.github/workflows/image.yml` runs `scripts/cli_smoke.py`
against the locally built all-in-one image: a healthy `single` install, a
refused second install, a backup restored onto a fresh directory, an upgrade
whose health check is forced to fail, and `doctor` on a fixture.

The forced failure is `SUPERSTEP_UPGRADE_HEALTH_FAIL=1`. That variable is the
smoke-test hook. It is not an operator flag. `doctor` on the fixture reports
`STUDIO_ENV` unset, the placeholder `JWT_SECRET`, and a missing Docker socket.
