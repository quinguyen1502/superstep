# Development

## Repository layout

| Path | Contents |
| --- | --- |
| `backend/app/` | FastAPI app, layered `core / models / schemas / repositories / services / api / engine` |
| `backend/tests/` | pytest suite, including layer, envelope and catalogue checks |
| `frontend/` | React, TypeScript, Vite, React Flow, Tailwind v4, shadcn/ui |
| `frontend/e2e/` | Playwright specs |
| `docker/studio-code/` | The Code mode sandbox image |
| `handbook/` | This site (Zensical, MkDocs-format config) |
| `scripts/` | Compose smoke test, the quickstart video renderer |
| `docs/` | Error catalogue, backend architecture and UI conventions |
| `.env.example` | Every Compose and runtime variable |
| `.factory/`, `.factory-state/` | The delivery workflow: requirements, decisions, tasks, reviews and QA |

## Tests

```bash
cd backend && .venv/bin/python -m pytest -q
cd frontend && npm run build && npm run lint && npm test
```

Install the backend with `pip install -e "backend[dev]"`. Postgres and Redis
locally:

```bash
cd backend
DATABASE_URL=postgresql://… TEST_DATABASE_URL=postgresql://… \
  REDIS_URL=redis://localhost:6379/0 .venv/bin/python -m pytest -q
```

The Postgres tests need a role with `CREATEDB`.

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs pytest on Python 3.12 (also on
Postgres 17 and Redis 7), the frontend lint and build on Node 20 and 22, and a Compose
smoke test. `handbook.yml` builds this handbook strictly and publishes it from
`main`. `factory-verify.yml` checks the factory metadata. End-to-end tests are
not on CI.

## End-to-end tests

Playwright starts its own API on port 8100 (with a temporary database), Vite
on 5190, a fake chat API and an SMTP sink.

```bash
cd frontend && npx playwright install chromium
npm run e2e
```

| Variable | Effect |
| --- | --- |
| `PW_CHROME` | Use an installed Chrome instead of Playwright's Chromium |
| `E2E_UVICORN`, `E2E_PYTHON` | Override the backend binaries |
| `E2E_API_PORT`, `E2E_UI_PORT` | Run two checkouts side by side |
| `E2E_CODE_RUNTIME=subprocess` | Run the Code mode specs without Docker |

CI runs the whole suite (English and Vietnamese) on every pull request in the
`E2E (Playwright)` job, split into three shards with `--shard`, Chromium cached and
`E2E_CODE_RUNTIME=subprocess`. Tests are not retried: a flaky test is fixed at its
cause. When a shard fails, its traces and screenshots are uploaded as the
`e2e-shard-N` artifact (kept 7 days); open a trace with `npx playwright show-trace`.

## Handbook screenshots

```bash
cd frontend && HANDBOOK_SHOTS=1 npm run e2e -- handbook quickstart
```

`e2e/handbook.spec.ts` seeds sample workflows, runs them, and writes
`handbook/docs/<en|vi>/images/*.png` at 1440 × 900. The Code mode shot needs
Docker and the `studio-code:1` image. `e2e/quickstart.spec.ts` follows the
[Quickstart](../start/quickstart.md) in the UI, writes its screenshots, and
records the frames the video is made from.

## The handbook

```bash
cd handbook
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/zensical serve -a 127.0.0.1:8001
```

The site is built with [Zensical](https://zensical.org) from MkDocs-format
config. English (`docs/en/`, `mkdocs.yml`) is served at `/` and Vietnamese
(`docs/vi/`, `mkdocs.vi.yml`) at `/vi/`; both share `mkdocs.base.yml` and the
same page tree. `strict: true` fails the build on a broken link or anchor.
[Error codes](errors.md) is included from `docs/api-errors.md`. See
`handbook/README.md` for the build commands.

## The quickstart video

`scripts/promo/` renders the video on the home page from the frames that
`e2e/quickstart.spec.ts` records: an HTML timeline moves a cursor to the
recorded position of each control, Chrome renders it frame by frame, and
ffmpeg encodes it with a generated music bed. See `scripts/promo/README.md`.

## Contribution workflow

Work follows the AI Software Factory in `.factory/` (see `AGENTS.md`):
requirements, decisions and tasks live in `.factory-state/`, each task gets a
branch `factory/task-<id>-<name>`, and a merge needs a human approval. Backend
changes keep the layers; schema changes go through Alembic; new error codes go
into the catalogue, `docs/api-errors.md` and both locales; UI strings go into
both locale files.

Frontend code follows `docs/ui-conventions.md`. Its alignment rule (shadcn
size variants instead of hand-set heights, paddings or line heights; toolbars
as `flex items-center` rows) is checked twice: `npm run lint` runs
`scripts/check-ui-classes.mjs`, and `e2e/alignment.spec.ts` measures the main
toolbars with `e2e/helpers/alignment.ts`. A justified exception carries an
inline `ui-class-ok: <reason>` comment.
