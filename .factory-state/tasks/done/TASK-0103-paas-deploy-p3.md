# Task

## Metadata

- Project: superstep
- Task ID: TASK-0103
- Status: done (backfilled)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: REQ-0060
- Design IDs: none
- Architecture IDs: none
- Pull request: [#121](https://github.com/quinguyen1502/superstep/pull/121) `feat/paas-deploy-p3`
- Merge commit: `008b027c6632c7f621a3afdcbade7d22c2c94a57` (2026-10-24)

## Objective

PaaS deploy phase 3: remote sandbox service for Code nodes.

> Backfilled 2026-10-24 (TASK-0093): reconstructed from the PR description and diff after the fact; the work was merged outside the factory workflow, so no task, review or QA record existed at the time.

## Scope (from the PR)

- **Engine abstraction:** `CodeRunner` (`problem(lang)`, `exchange(lang, payload, seconds, cancelled)`) with `DockerRunner`, `SubprocessRunner` and `RemoteRunner` in `RUNNERS`. `run_code` and `unavailable` only use the interface; behaviour of `docker` and `subprocess` is unchanged.
- **`STUDIO_CODE_RUNTIME=remote`:** `engine/sandbox/remote.py` calls the service with Bearer `STUDIO_SANDBOX_TOKEN`. The info check is cached for 30 s. Cancels are forwarded. Failures map to the existing `CODE_RUNTIME_UNAVAILABLE` code, so no new error codes were added.
- **`app/sandbox_service.py`:** a stdlib HTTP server. It requires a token of 16+ characters and uses the studio envelope with catalog codes (`AUTH_TOKEN_INVALID`, `PAYLOAD_TOO_LARGE`, `NOT_FOUND`, `VALIDATION_ERROR`, `CODE_LANGUAGE_UNSUPPORTED`). Each call runs through `SubprocessRunner` with an empty env, a temp dir, rlimits and the time limit. When running as root, each concurrent call gets its own uid (`STUDIO_CODE_RUN_AS`, default 61000+).
- **No network by default:**
- **Image:** `docker/studio-sandbox/Dockerfile` contains only the Code runtime modules, httpx, pydantic/dateutil, and Deno with the cached allowlist. It is published as `ghcr.io/quinguyen1502/superstep-sandbox` through the same workflow (publish matrix) and scanned by Trivy.
- **Wiring:**
- **UI:** a "Sandbox service (remote)" / "Dịch vụ sandbox (remote)" runtime label, and a success badge when the service is available. These are small hunks, away from the #117 changes.
- **Docs:** `docs/deploy/sandbox(.vi).md` gives an honest security model: process isolation, not container or VM isolation; the Python block is an in-interpreter guard; Render and Fly private services still have egress; Docker on your own server remains stronger. Fly Machines and Northflank sandboxes are mentioned only as possible future backends. The env var reference and `.env.example` are updated.
- **Tests:**

## Changed files

- 25 files: `.env.example`, `.github/workflows/image.yml`, `backend/app/core/config.py`, `backend/app/engine/code_languages.py`, `backend/app/engine/code_runtime.py`, `backend/app/engine/sandbox/code_runner.py`, `backend/app/engine/sandbox/remote.py`, `backend/app/sandbox_service.py`, `backend/tests/test_code_remote.py`, `deploy/fly/sandbox.fly.toml`, `deploy/render/render.full.yaml`, `docker-compose.yml`, `docker/studio-sandbox/Dockerfile`, `docs/deploy/README.md`, `docs/deploy/README.vi.md`, `docs/deploy/env-vars.md`, `docs/deploy/env-vars.vi.md`, `docs/deploy/sandbox.md`, `docs/deploy/sandbox.vi.md`, `frontend/src/components/code-runtime-card.tsx`, `frontend/src/lib/code-runtime.ts`, `frontend/src/locales/en.json`, `frontend/src/locales/vi.json`, `scripts/check_deploy_configs.py`, `scripts/sandbox_smoke.py`.

## Activity Log

- 2026-10-24: merged into develop (008b027).
- 2026-10-24: task record backfilled (TASK-0093); verified retroactively on develop by QA-0085.

## Handoff Notes

- Review REV-0095, QA QA-0095 (retroactive records).
