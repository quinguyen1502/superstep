# Task

## Metadata

- Project: superstep
- Task ID: TASK-0080
- Status: done (PR #110)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-23
- Updated: 2026-10-23
- Requirement IDs: REQ-0046
- Design IDs: none
- Architecture IDs: DEC-0049

## Objective

Run `export function main(state)` written in TypeScript with the same contract, limits and error codes as Python.

## Scope

### In Scope

- `engine/sandbox/code_runner.ts` (Deno, std only): stdin `{source, state, stdout_max}`, one JSON result line, console capture, `<code>` frames only, `not_json` for undefined/BigInt/functions/cycles, sync or async `main`.
- `TypeScript` strategy in `code_languages.py`: static check (export main, import allowlist), `deno run --no-prompt` with no `--allow-*` flag, V8 heap cap from `STUDIO_CODE_MEMORY`, `--no-remote`, `--cached-only`, `--no-config`, own `DENO_DIR` per call on the host.
- Config: `STUDIO_CODE_LANGUAGES` default `python,typescript`, `STUDIO_CODE_TS_IMAGE` (`studio-code-ts:1`), `STUDIO_CODE_TS_PACKAGES` (pinned `name@major`, default `npm:zod@3,npm:date-fns@4`, equal to `deps.ts`; imports must use the same major), `STUDIO_DENO` (binary for the subprocess runtime).
- `docker/studio-code-ts/Dockerfile` (denoland/deno, pre-cached allowlisted npm packages, non-root, no network at run time); compose env.
- Backend tests for both languages (subprocess runtime with a real Deno).

### Out of Scope

- P3 items of REQ-0046 (type-check diagnostics, LangGraph.js export, full IntelliSense).

## Tests

- `tests/test_code_typescript.py`, parametrised language tests.

## Progress Log

- 2026-10-23: CI fix: moved the inline comment off the USER line in docker/studio-code-ts/Dockerfile (Docker parsed it as part of the user); owner approved the merge; merged into develop (PR #110).
- 2026-10-23: CI fix: allowlist entries pinned to `name@major` (`npm:zod@3,npm:date-fns@4`), `deps.ts` caches exactly those, and the import check refuses unversioned or other-major imports, naming the allowed spec (an unversioned `npm:zod` resolved to zod 4, which the image does not cache).

## Handoff Notes

- Backfilled 2026-10-24 (TASK-0093): Review REV-0073; QA QA-0073; develop verified retroactively by QA-0085.
