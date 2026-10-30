# Task

## Metadata

- Project: superstep
- Task ID: TASK-0149
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-10-27
- Updated: 2026-10-27
- Requirement IDs: REQ-0079
- Design IDs: none
- Architecture IDs: DEC-0068

## Objective

Ship the `superstep` command and the server version it compares against. The command has help, JSON, English and Vietnamese, and shell completion. Later phase 1 tasks add the other commands on this parser.

## Scope

### In Scope

- `sdk/python/src/superstep/cli/` and the console script `superstep`, as DEC-0068 decision 1. The `cli` extra is declared and adds no dependency.
- The shared parser (decision 2): `--help` with an example, `--json`, `--lang`, and `superstep completion bash|zsh|fish`.
- Catalogs `locales/en.json` and `locales/vi.json` with the same keys. Language order is `--lang`, then `~/.superstep/cli.json`, then `LANG` / `LC_MESSAGES`.
- `superstep version`. It prints the CLI version from `superstep.__version__` and, given a base URL, the server version from `GET /api/health` → `data.version`. A missing version or a different `major.minor` warns and still exits 0.
- `GET /api/health` gains `version`, the `superstep-backend` package version (decision 7). The envelope stays. No new route.
- Unit tests for the parser, the catalogs, JSON on stdout, and the health field.

### Out Of Scope

- install, status, doctor, backup, upgrade, admin, uninstall, deploy (TASK-0150 to TASK-0155).
- `scripts/install.sh`, the `v*` package publish, and the new images (TASK-0156).
- Phase 2 commands (DEC-0068 decision 11).

## Inputs

- REQ-0079 groups D, E (the version field) and F (the package only).
- DEC-0068 decisions 1, 2 and 7.
- `sdk/python/pyproject.toml`, `sdk/python/src/superstep/_version.py`, `backend/app/api/routes/meta.py`, `backend/app/schemas/envelope.py`.

## Related Artifacts

- Requirements: `.factory-state/artifacts/REQ-0079-superstep-cli.md`
- Design: none
- Architecture: `.factory-state/decisions/DEC-0068-superstep-cli.md`
- Decisions: `DEC-0010-api-envelope-error-codes-i18n.md`, `DEC-0009-layered-backend-sqlalchemy-alembic.md`
- Discovery: `.factory-state/artifacts/DISC-0001-project-context.md`
- Clarifications: `.factory-state/artifacts/CLAR-0010-superstep-cli.md`

## Expected Outputs

- `superstep --help` and `superstep version` run from an editable install of `sdk/python`.
- `/api/health` reports the backend version inside `data`.

## Implementation Notes

- Keep the CLI importable without the server package. The health change is a field on the existing payload in `meta.health`.
- Do not bump `_version.py` to the server version here. TASK-0156 does that on the release. Tests pass the versions in.
- CLI error codes stay in the CLI package. Do not add them to `core/errors.py` or the frontend locales.
- Human text goes to stderr. `--json` writes one object to stdout.

## Constraints

- SDK floor stays Python >= 3.9. No `tomllib`, Click, or Typer.
- The health route stays public and on the envelope. `tests/test_api_envelope.py` must pass.
- No FastAPI in a service. This task does not add a service.

## Dependencies

- None. Based on `develop` (DEC-0033).

## Acceptance Criteria

- `superstep --help` and `superstep version --help` exit 0 and each shows an example.
- `--json` writes a single object to stdout. A failure is `{"ok": false, "error": {"code", "message"}}` and a non-zero exit. The message is in the selected language.
- The en and vi catalogs have the same keys. `--lang vi` and `LANG=vi` select Vietnamese. `--lang en` wins over `LANG`.
- `superstep completion bash`, `zsh` and `fish` each mention `version`.
- `GET /api/health` returns `data.version` equal to the `superstep-backend` version, and the existing health fields.
- `superstep version --url <base>` warns when `data.version` is absent or the `major.minor` differs, and exits 0. It prints no secret.

## Validation Plan

- `cd sdk/python && python -m pytest -q`
- `cd backend && .venv/bin/python -m pytest -q tests/test_api_envelope.py tests/test_run_bus.py`

## Assumptions

- The designer step is skipped. REQ-0079 already specifies help, JSON and the two languages (DEC-0068).
- A base URL with no running server is a connection error, not a version warning. The warning is for a server that answers and has no version or a different `major.minor`.
- The completion script is written to stdout so a shell can source it. Help, version text and errors stay on stderr. `--json` still writes one object to stdout.

## Open Questions

- None.

## Activity Log

- 2026-10-27: planned from REQ-0079 phase 1 (DEC-0068).
- 2026-10-27: owner confirmed the phase 1 set. Branch `factory/task-0149-cli-foundation` from `develop` at `31a2d26`. Task moved to doing. No source edited.
- 2026-10-27: implemented the CLI package, catalogs, `version`, `completion`, and `data.version` on `/api/health`. Tests were added with the task and were not run.
- 2026-10-27: validation passed on the uncommitted task changes. Tool policy: backend pytest 773 passed, 57 skipped (327s, includes `test_health_version`, `test_api_envelope`, `test_run_bus`); sdk/python pytest 40 passed, 2 skipped (0.50s, includes `test_cli`); frontend lint exit 0 (5 existing warnings); frontend test 123 passed; frontend build exit 0; TypeScript SDK test 22 passed, build exit 0, typecheck exit 0.
- 2026-10-27: review REV-0129. No blocking findings. Approved for QA. Task stays in doing.
- 2026-10-27: QA QA-0129. Pass with follow-up. CLI tests 18 passed; health, envelope and run-bus tests 17 passed; `python -m superstep.cli` help, version and completion checked.
- 2026-10-27: owner asked to move the task to done. Review REV-0129 has no blocking findings. QA-0129 passed with the documented URL and console-script risks. Not merged.

## Handoff Notes

- TASK-0150 adds `install` on this parser and is the first command that talks to Docker.
- Review: `.factory-state/artifacts/REV-0129-task-0149.md`. QA: `.factory-state/artifacts/QA-0129-task-0149.md`.
- An editable install made before this change does not yet have the `superstep` script on `PATH`. `pip install -e sdk/python` refreshes it. Tests call `superstep.cli.run`.
