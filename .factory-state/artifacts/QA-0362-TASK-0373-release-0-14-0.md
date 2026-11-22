# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0362
- Task ID: TASK-0373
- QA Owner: Codex
- Created: 2026-11-22
- Updated: 2026-11-22
- Outcome: local and reviewed-head CI validation passed

## Acceptance Criteria Coverage

- Server, frontend, Python SDK, CLI and installer agree on 0.14.0. Python SDK and installer suite passed (264 passed, 11 optional or live cases skipped). Built the wheel from the source distribution, installed it and confirmed `superstep version` prints 0.14.0.
- TypeScript SDK 0.4.0 and React toolkit 0.1.5 agree with the workspace lockfile. Workspace install, production build and lint passed. TypeScript generation and type checks, ESM/CommonJS package smoke and npm dry-run packs passed. Vitest passed for Studio (191), TypeScript SDK (117) and React (22). Verified the React peer range accepts the 0.2, 0.3 and 0.4 SDK series.
- The release notes cover the integrated Dataset features and the opt-in Formula preview. The pre-existing Dataset and its row survived an upgrade from revision 0071 to 0074 on both SQLite and PostgreSQL 17, then a second startup ran idempotently. Focused backend tests passed (41 passed, 32 optional service cases skipped in the SQLite run).
- Both handbook builds passed strict mode and the image check. Deployment config validation, published OpenAPI/AsyncAPI drift check, installer syntax, strict YAML and Factory hygiene passed. Publisher jobs remain tag-triggered with the existing permissions.
- GitHub and the public registries had no v0.14.0, sdk-ts-v0.4.0 or sdk-react-v0.1.5 release at preparation time.

## Evidence

- Commands covered the root npm build, lint and test, SDK generator and package scripts, Python SDK pytest and build, and the programmatic Alembic upgrade on two disposable databases.
- Source review is recorded in [REV-0362](REV-0362-TASK-0373-release-0-14-0.md).

## Gaps And Follow-Up

- The [reviewed PR head](https://github.com/quinguyen1502/superstep/pull/433/checks) passed all 25 CI checks, including the Node matrix, PostgreSQL/Redis, all three Playwright shards and image smoke checks. Verify the final state-only head before merge.
- The main promotion, final changelog date, and publication are separate owner-approved steps. Recheck version availability against the exact source revision before tagging.

## QA Decision

Passed candidate validation. Final integration remains gated by checks on the merged source. Production publication follows the main promotion.

## Promotion Preflight

- A simulated merge into main at `3e996e57` found only a changelog conflict with the previous release date. Keeping the candidate changelog preserves that historical date and the new candidate entry. The simulated result also preserved main's 0.13.0 publication record. Apply the verified resolution and set the actual release date on the promotion branch.
