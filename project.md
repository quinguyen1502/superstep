# Project

## Name

superstep (named langgraph-studio up to v0.1.0, renamed in TASK-0058)

## Domain

- Developer tooling for LLM agent workflows (LangGraph)

## Actors

- Internal developer / learner (authenticated user)
- Project owner / administrator
- External LangGraph repositories (import source)

## Modules

- `packages/react/` — shared chat presentation, shadcn primitives and pure rendering helpers; Studio-owned routing/run access stays in frontend.
- Root npm workspace / lockfile: `frontend`, `packages/react`, `sdk/typescript` (TASK-0223).
- `frontend/` — React SPA: login/register, workflow list, editor (canvas, palette, config, run panel), import dialog
  - the editor page (`pages/Editor.tsx`) is a shell; state and actions are in `components/editor/use-studio.ts`, the header and panels in `components/editor/` (TASK-0040)
- `backend/app/` — layered FastAPI backend (DEC-0009, `docs/backend-architecture.md`):
  - `main.py` app factory; `api/` routers (REST + `/ws/run`), deps, error handlers
  - `services/` business rules; `repositories/` SQLAlchemy queries; `models/` ORM models + `Database`; `migrations/` Alembic
  - `engine/` validator, StateGraph compiler, nodes, LLM/tools, runtime streaming, limits, repo import + `sandbox/runner.py`
  - `core/` config (env vars), security (hashing, JWT), domain errors; `schemas/` Pydantic DTOs
- `backend/tests/` — pytest suite
- `frontend/e2e/` — Playwright specs (own API on :8100 and Vite on :5190); `frontend/src/lib/__tests__/` — vitest

## Constraints

- Internal use; must run offline in mock mode; SQLite by default, PostgreSQL + Redis through `DATABASE_URL` / `REDIS_URL` (REQ-0008)
- Repo import is experimental and off by default (`STUDIO_ENABLE_IMPORT`); imported code runs in a Docker sandbox (REQ-0009)
- Outbound HTTP (webhooks, MCP, HTTP Tool nodes) goes through the shared SSRF guard in `backend/app/core/net.py` (REQ-0027)
- UI: shadcn/ui components and theme tokens only, no hard-coded colours (DEC-0008, `docs/ui-conventions.md`)

## Declared Technology Direction

- Frontend: React + TypeScript (Vite), @xyflow/react, Tailwind CSS v4, shadcn/ui (Preferred, DEC-0001; observed in `frontend/package.json`)
- Mobile: none
- Backend: FastAPI + langgraph, Python >= 3.12 (Preferred; `backend/pyproject.toml`; CI uses 3.12)
- Database: SQLite default, PostgreSQL 17 + Redis 7 (observed: `docker-compose.yml`, CI job `backend-postgres`)
- Infrastructure: `dev.sh` local script and Docker Compose (observed)
- Ci Cd: GitHub Actions (Approved, DEC-0001; `.github/workflows/ci.yml` + `factory-verify.yml`)
- Deployment: Docker Compose (nginx UI + API + worker); no hosted target
- Testing: pytest, vitest, tsc/vite build, oxlint, Playwright e2e (observed; e2e is not on CI)

## Technology Discovery

- Install: `./dev.sh` (creates or repairs `backend/.venv`: `pip install --prefer-binary -e "backend[dev]"`, then root `npm install`); Factory: `factory deps apply --allow-network`
- Run: `./dev.sh` (observed: backend :8000, frontend :5173)
- Test: root `npm test` covers frontend, React package and TypeScript SDK; `npm run test:e2e` runs frontend Playwright. Backend: `cd backend && .venv/bin/python -m pytest -q` (observed: 324 passed, 10 skipped without Postgres/Redis, 2026-10-18); `cd frontend && npm test` (vitest); `cd frontend && npm run e2e` (Playwright; `PW_CHROME`, `E2E_UVICORN`)
- Build: root `npm run build` (SDK, React package, frontend/widget; observed TASK-0223)
- Lint: root `npm run lint` (frontend + shared React package; strict UI guard includes both source trees)
- Typecheck: `cd frontend && npx tsc -b` (observed, part of build)
- Format: Unknown
- Migration: Alembic (`backend/app/migrations/versions`, applied at startup under a file or advisory lock)

## Assumptions

- Stack choices are Preferred by owner decision (DEC-0001); CI is Approved.
- The integration branch is `develop` (DEC-0033). GitHub Actions does not run while the account's billing blocks it (owner decision, 2026-10-18); local checks are the evidence.

## Open Questions

- None (resolved by DEC-0001..DEC-0005).
