# Task

## Metadata

- Project: superstep
- Task ID: TASK-0102
- Status: done (backfilled)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: REQ-0060
- Design IDs: none
- Architecture IDs: none
- Pull request: [#120](https://github.com/quinguyen1502/superstep/pull/120) `feat/paas-deploy-p2`
- Merge commit: `d7eb8b35fce939bd58aa3e664636e694b77dcae7` (2026-10-24)

## Objective

PaaS deploy phase 2: Fly.io, DigitalOcean, Koyeb, Zeabur, Northflank, self-hosted guide.

> Backfilled 2026-10-24 (TASK-0093): reconstructed from the PR description and diff after the fact; the work was merged outside the factory workflow, so no task, review or QA record existed at the time.

## Scope (from the PR)

- **Fly.io:** `fly.toml` uses the GHCR image, a `/data` volume, the `/api/health` check, and auto-stop (documented). The docs cover `fly launch --copy-config`, the volume, secrets and the Postgres option.
- **DigitalOcean App Platform:** `.do/deploy.template.yaml` and a button. It uses the GHCR image and a managed Postgres dev database, because App Platform has no volumes. `STUDIO_PUBLIC_URL` is set to `${APP_URL}`. App Platform can't generate secrets, so the template has `change-me` values that the user must replace on the review screen.
- **Koyeb:** a button with the GHCR image on port 8000 and empty env fields to fill in. Postgres is required, since free instances have no volume.
- **Zeabur:** `deploy/zeabur/template.yaml` (PREBUILT GHCR image, `/data` volume, `JWT_SECRET` from `${PASSWORD}`). It is deployed with the CLI and **not published** to the marketplace.
- **Northflank:** step-by-step docs (external image, secret group, volume or PostgreSQL addon). No template is published.
- **Coolify / Dokploy:** `docs/deploy/self-hosted(.vi).md` is the full-feature path, using `docker-compose.yml` with Docker-socket sandboxes. It covers building the images, `STUDIO_DOCKER_GID`, the domain on `web:80`, operations, and an honest security model (socket = root-equivalent; containers share the kernel; the fixed pgvector volume name).
- **Image:** a new `docker/entrypoint.sh` starts as root only to chown a root-owned `/data` mount (Fly, Railway, Render, Zeabur), then drops to the `studio` user with `setpriv`. This replaces the Railway `RAILWAY_RUN_UID=0` note.
- **CI:**
- **README:** DigitalOcean and Koyeb buttons in the Deploy section (the lines added in #119, away from the README areas #117 changes).

## Changed files

- 13 files: `.do/deploy.template.yaml`, `.github/workflows/image.yml`, `Dockerfile`, `README.md`, `README.vi.md`, `deploy/zeabur/template.yaml`, `docker/entrypoint.sh`, `docs/deploy/README.md`, `docs/deploy/README.vi.md`, `docs/deploy/self-hosted.md`, `docs/deploy/self-hosted.vi.md`, `fly.toml`, `scripts/check_deploy_configs.py`.

## Activity Log

- 2026-10-24: merged into develop (d7eb8b3).
- 2026-10-24: task record backfilled (TASK-0093); verified retroactively on develop by QA-0085.

## Handoff Notes

- Review REV-0094, QA QA-0094 (retroactive records).
