# CLI

`superstep` installs, upgrades and backs up one instance on a machine that has
Docker and Compose v2. The package version is the server version. On the `0.1.0`
line the Python package was the SDK only; a `v*` release moves that package to
the server version.

## Install

The one-line installer is `scripts/install.sh`. It refuses native Windows and
tells you to use WSL. When `uv` is missing it installs uv (that step does not
need Python), then runs `uv tool install 'superstep[cli]==<version>'`.

```bash
curl -fsSL https://raw.githubusercontent.com/quinguyen1502/superstep/develop/scripts/install.sh | sh
superstep install
```

`superstep install` asks for the topology (`single` or `full`), the public URL
and the admin e-mail. `--yes` with those flags skips the questions. The
all-in-one image is `ghcr.io/quinguyen1502/superstep`. The full stack uses
`superstep-api` and `superstep-web`. A second install into an existing instance
refuses to overwrite it.

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

## CI smoke test

`.github/workflows/cli.yml` runs the Python package tests on a pull request.
It does not publish. `.github/workflows/image.yml` runs `scripts/cli_smoke.py`
against the locally built all-in-one image: a healthy `single` install, a
refused second install, a backup restored onto a fresh directory, an upgrade
whose health check is forced to fail, and `doctor` on a fixture.

The forced failure is `SUPERSTEP_UPGRADE_HEALTH_FAIL=1`. That variable is the
smoke-test hook. It is not an operator flag. `doctor` on the fixture reports
`STUDIO_ENV` unset, the placeholder `JWT_SECRET`, and a missing Docker socket.
