# Superstep SDKs

Clients for the public workflow-trigger API (`/api/hooks/*`), generated from
and checked against [`docs/api/openapi.public.json`](../docs/api/openapi.public.json).

| Folder | Package | Docs |
| --- | --- | --- |
| [`python/`](python/) | `superstep` on PyPI | [README](python/README.md) |
| [`typescript/`](typescript/) | `@superstep/sdk` on npm | [README](typescript/README.md) |

## When the API changes

1. Change the backend (`backend/app/api/routes/hooks.py`, `backend/app/schemas/public_api.py`).
2. `python scripts/gen_public_openapi.py` (with the backend's Python) rewrites
   `docs/api/openapi.public.json` and the handbook copy.
3. `npm run gen` in `sdk/typescript` regenerates `src/schema.ts`; update the
   Python models until `sdk/python/tests/test_spec_sync.py` passes.
4. `scripts/sdk_integration.sh` runs both SDKs against a live local backend.

CI checks steps 2 and 3 (`backend/tests/test_public_openapi.py`,
`npm run gen:check`) and runs the unit and live tests.

## Releasing

`.github/workflows/sdk-publish.yml` publishes on a tag; nothing is published
from branches or pull requests.

| Tag | Publishes | Needs |
| --- | --- | --- |
| `sdk-py-v<version>` | `sdk/python` to PyPI | `__version__` in `src/superstep/_version.py` equals `<version>` |
| `sdk-ts-v<version>` | `sdk/typescript` to npm | `version` in `package.json` (and `VERSION` in `src/client.ts`) equals `<version>` |

One-time setup by a maintainer:

- **PyPI**: reserve the `superstep` project name, then add a trusted publisher
  (repository `quinguyen1502/superstep`, workflow `sdk-publish.yml`,
  environment `pypi`). No secret is needed. Without trusted publishing, add a
  `PYPI_API_TOKEN` secret to the `pypi` environment and pass it as
  `password:` to the publish step.
- **npm**: create the `superstep` organisation (scope `@superstep`), then add
  an automation token as the `NPM_TOKEN` secret of the `npm` environment.
  Packages are published with provenance.
- **GitHub**: create the `pypi` and `npm` environments (Settings, Environments),
  optionally with required reviewers so each release needs an approval.
