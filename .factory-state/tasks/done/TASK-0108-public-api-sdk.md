# Task

## Metadata

- Project: superstep
- Task ID: TASK-0108
- Status: done (backfilled)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: REQ-0064
- Design IDs: none
- Architecture IDs: none
- Pull request: [#127](https://github.com/quinguyen1502/superstep/pull/127) `feat/public-api-sdk`
- Merge commit: `1504fc656c72824b0d9ce9fadca3eb6fb405c993` (2026-10-24)

## Objective

Public API contract, Python and TypeScript SDKs.

> Backfilled 2026-10-24 (TASK-0093): reconstructed from the PR description and diff after the fact; the work was merged outside the factory workflow, so no task, review or QA record existed at the time.

## Scope (from the PR)

- The public routes moved to `api/routes/hooks.py` (tag `public`, unchanged paths and behaviour). Owner token management stays in `triggers.py`.
- Security schemes `WorkflowToken` (apiKey header `X-Workflow-Token`) and `WorkflowBearer` (HTTP bearer); `X-Workflow-Token` still wins.
- Typed models in `schemas/public_api.py` (`StartRunRequest`, `RunAccepted`, `RunPending`, `RunResult`, `RunMetrics`, `RunWaiting`, named envelopes). `schemas/envelope.py` adds `ErrorEnvelope` and `error_responses(*codes)`, which builds the error responses with examples from `core/errors.py` `CATALOG`, so the codes have one source.
- operationIds `startRun` / `getRun`; 200/202 bodies typed; `Location` header documented and now also sent on async starts.
- Public-only spec: `GET /openapi.public.json`, Swagger view at `/docs/public`; `/docs` and `/openapi.json` unchanged.
- `scripts/gen_public_openapi.py [--check]` writes `docs/api/openapi.public.json` and the handbook copy. `tests/test_public_openapi.py` fails when the committed files are stale. It also checks the security, tags, operationIds and that responses have no untyped bodies, and validates real responses against the models (this caught `metrics.duration_ms` being a float).
- `run/public-api.md`: concepts, creating a token in the UI, start, poll, run and wait, install, errors and codes with SDK exceptions, rate limits, OpenAPI locations. Every step has curl / Python / TypeScript tabs.
- `reference/public-api.md`: rendered from the spec with **Redoc 2.5.4 vendored** (`javascripts/vendor/redoc.standalone.js`, MIT). The vi pages symlink the asset and the spec, the same way `extra.css` is shared.
- Nav entries in both languages; links from API triggers, HTTP API, README and README.vi.
- `sdk/python` (`superstep`, httpx, Python 3.9+): `Client` / `AsyncClient`, `run`, `get_run`, `wait`, `run_and_wait(timeout, poll_interval, max_poll_interval, backoff)`, frozen dataclass models, errors typed by code and then by HTTP status, `SUPERSTEP_*` env fallback. `tests/test_spec_sync.py` checks the models and the error map against the spec.

## Changed files

- 71 files: `.github/workflows/ci.yml`, `.github/workflows/sdk-publish.yml`, `CHANGELOG.md`, `README.md`, `README.vi.md`, `backend/app/api/openapi_public.py`, `backend/app/api/routes/__init__.py`, `backend/app/api/routes/hooks.py`, `backend/app/api/routes/triggers.py`, `backend/app/main.py`, `backend/app/schemas/envelope.py`, `backend/app/schemas/public_api.py`, `backend/app/schemas/trigger.py`, `backend/tests/test_public_openapi.py`, `docs/api/openapi.public.json`, `docs/backend-architecture.md`, `handbook/docs/en/javascripts/api-reference.js`, `handbook/docs/en/javascripts/vendor/redoc.standalone.js`, `handbook/docs/en/javascripts/vendor/redoc.standalone.js.LICENSE.txt`, `handbook/docs/en/reference/api.md`, `handbook/docs/en/reference/openapi.public.json`, `handbook/docs/en/reference/public-api.md`, `handbook/docs/en/run/api-triggers.md`, `handbook/docs/en/run/public-api.md`, `handbook/docs/en/stylesheets/extra.css` and more.

## Activity Log

- 2026-10-24: merged into develop (1504fc6).
- 2026-10-24: task record backfilled (TASK-0093); verified retroactively on develop by QA-0085.

## Handoff Notes

- Review REV-0100, QA QA-0100 (retroactive records).
