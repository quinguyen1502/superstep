# Task

## Metadata

- Project: superstep
- Task ID: TASK-0101
- Status: done (backfilled)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: REQ-0060
- Design IDs: none
- Architecture IDs: none
- Pull request: [#119](https://github.com/quinguyen1502/superstep/pull/119) `feat/paas-deploy`
- Merge commit: `b2ac4b0fa736a640c6ee56a06cb9e7e0fbfa6f7e` (2026-10-24)

## Objective

PaaS deploy phase 1: all-in-one image and one-click deploys.

> Backfilled 2026-10-24 (TASK-0093): reconstructed from the PR description and diff after the fact; the work was merged outside the factory workflow, so no task, review or QA record existed at the time.

## Scope (from the PR)

- **Root `Dockerfile`**: one container serves the built UI, `/api` and `/ws/run` on `$PORT`. It bundles Deno (TypeScript Code nodes) and uses `STUDIO_CODE_RUNTIME=subprocess`, labelled "Runs on host" as before. SQLite lives in `/data`, or Postgres comes via `DATABASE_URL`. `STUDIO_ENV=production` is set. No secrets are in the image.
- **Backend**
- **Platforms**
- **CI** (`.github/workflows/image.yml`, a new file so it doesn't conflict with `ci.yml` in #117):
- **Docs**: `docs/deploy/` in en and vi (vi follows the glossary), the env var reference, `.env.example`, and Deploy buttons in the README.
- **README / #117:** the buttons are in a new section just above "Documentation" / "Tài liệu". #117 only edits the top of both READMEs, so this should merge cleanly. `ci.yml` is untouched.
- **Default branch:** the Render and Heroku buttons deploy the default branch (`main`). They will work once this ships in a release.
- **Trusted proxies:** the image defaults `STUDIO_TRUSTED_PROXIES` to the private ranges plus 100.64.0.0/10. The PaaS router's peer is then trusted, and the client IP is the right-most untrusted XFF hop.
- **Railway volumes** need `RAILWAY_RUN_UID=0` (the volume is owned by root). This is in the docs.
- **Not done here:** the handbook pages (they overlap with #117) and the remote sandbox (Phase 3).

## Changed files

- 26 files: `.dockerignore`, `.env.example`, `.github/workflows/image.yml`, `Dockerfile`, `README.md`, `README.vi.md`, `app.json`, `backend/app/api/static.py`, `backend/app/core/config.py`, `backend/app/core/crypto.py`, `backend/app/main.py`, `backend/app/services/seed.py`, `backend/tests/test_paas_deploy.py`, `deploy/compose/docker-compose.single.yml`, `deploy/render/render.full.yaml`, `deploy/render/render.postgres.yaml`, `docker-compose.yml`, `docs/deploy/README.md`, `docs/deploy/README.vi.md`, `docs/deploy/env-vars.md`, `docs/deploy/env-vars.vi.md`, `heroku.yml`, `railway.json`, `render.yaml`, `scripts/compose_smoke.py` and more.

## Activity Log

- 2026-10-24: merged into develop (b2ac4b0).
- 2026-10-24: task record backfilled (TASK-0093); verified retroactively on develop by QA-0085.

## Handoff Notes

- Review REV-0093, QA QA-0093 (retroactive records).
