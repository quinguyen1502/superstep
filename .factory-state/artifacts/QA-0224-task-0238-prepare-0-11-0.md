# QA Report

## Metadata

- Project: superstep
- QA ID: QA-0224
- Task ID: TASK-0238
- QA Owner: Codex (advisory)
- Created/Updated: 2026-11-03
- Outcome: local and reviewed-head CI acceptance pass; owner accepted and authorised release

## Validation Scope

0.11.0 preparation on integrated develop d2119965, including shared version/pin/lock coherence, release notes, packaged client/runtime assets and migration/backup preservation. References: TASK-0238, accepted DEC-0084, PLAN-0002, REV-0224 and prior feature REV/QA-0222/0223. No release tag, registry upload, main release merge, deployment, native completion or live provider cutover is performed.

## Acceptance Criteria Coverage

| Criterion | Result/evidence |
| --- | --- |
| Shared version/pins/lock/runtime | Backend pyproject, Python _version, frontend package/lock and install.sh agree on 0.11.0. Refreshed installed metadata and actual /api/health report backend 0.11.0. CLI version --json and the independently installed wheel report 0.11.0. Existing release/installer tests pass in the full profile. |
| Accurate release grouping/docs | Changelog 0.11.0 includes merged chat phases 1–3/edit/regenerate, generic managed HTTP/channel/Google tools, events/fallback, portable expense template and prior fixes. Native is deferred. A byte comparison preserves historical 0.10.2-and-earlier notes. Strict en/vi handbook/media pass. |
| Python artifacts | sdist -> wheel build succeeds. The installed wheel imports from the temporary target, includes sync/async regenerate, py.typed, token/stream/core modules, CLI locales and bundled 0.11.0 changelog. CLI runs from that installed artifact. The installed wheel excludes tests/evidence/env files; the sdist retains 22 source test files and its build hook, with no evidence/environment files. |
| npm artifacts | SDK 0.2.0 has 82 files; React 0.1.0 has 102. Extracted packages load in a temporary consumer that uses these tarballs for @superstep, with existing peer dependencies only. SDK ESM/CJS revision methods/store and server mintChatToken export pass; React Chat/Provider/MessageList/Composer/useChat, CSS and en/vi generated messages are present. No tests/screenshots/env archives are included. |
| Migration/backup | Build a synthetic 0049_review_recovery SQLite fixture (v0.10.2 head), insert original chat/root/answer/file/rating via reflected SQLAlchemy tables and back it up using SQLite backup. Upgrade to 0054_chat_regenerate twice, verify preserved text/blob/rating and empty lineage defaults; restore a copy of the backup and upgrade it successfully. Original backup remains at 0049 and readable. |
| Declared/full validation | All 8 Factory commands pass in superstep-0238-verify-full.log. Structure/verification/ID checks pass; dependency validation passes with version-only manifest-fingerprint warning. Full remote SQLite/Postgres/Redis/MinIO, E2E, React 18/19 and image checks remain required on the exact PR head. |

## Checks Performed

- Canonical full profile: PATH includes backend venv, ARM Node wrapper and Deno; all eight declared commands pass. Log /private/tmp/superstep-0238-verify-full.log.
- Strict handbook: superstep-0238-handbook-en.log, -vi.log, -images.log; all pass.
- Package build: temporary build environment follows existing setuptools/hatchling/build workflow requirements; superstep-0238-python-build.log builds sdist and then wheel. Outputs are /private/tmp/superstep-0238-packages.
- Independent wheel install/import and installed CLI 0.11.0 pass; superstep-0238-wheel-install.log and observed runtime output. Target /private/tmp/superstep-0238-installed. Actual /api/health uses a separate temporary SQLite/key/import path, not user data; version 0.11.0, run_bus_ok true.
- npm pack uses a task-local cache; JSON inventories superstep-0238-pack-{sdk,react}.json. Artifact consumer /private/tmp/superstep-0238-npm-consumer; superstep-0238-npm-smoke.log reports ESM/CJS, React assets and signing exports passed.
- Migration check /private/tmp/superstep-0238-migration-check.py; superstep-0238-migration.log reports upgrade/restore passed and attachment SHA256 bafd962b625070d6bc1827fbf87d01b6401a9f92cd38874dfbc5d73007acdc74. Fixture/backup/restore files stay outside Git.
- Registry inspection (2026-11-03, read-only): official PyPI JSON reports current 0.10.2 and no 0.11.0 entry; npm SDK current 0.1.0, React returns E404/no public metadata. Sources: https://pypi.org/pypi/superstep/json and configured npm registry. No upload/tag operation was made.

## Local Build Receipt

These are the locally inspected artifacts, not registry publication receipts. Hashes are also recorded in superstep-0238-package-hashes.json outside Git.

| Artifact | Bytes | SHA256 |
| --- | ---: | --- |
| `superstep-0.11.0-py3-none-any.whl` | 115758 | `616e95bdb76b67936ac7546235c1de1d3d74ef8c0b20e61e0f8dc7c562af9927` |
| `superstep-0.11.0.tar.gz` | 140850 | `37132b8f439452b457564f59d50bded7e15f337480f85b2d2ef7791986113ea6` |
| `superstep-react-0.1.0.tgz` | 92729 | `dce8524d4e18d5ad21102b3c48e25e02f091fdf8abd591ab67e23329348d7393` |
| `superstep-sdk-0.2.0.tgz` | 52649 | `ac45acf5d3043bacec1a72d5429a9fec4d3198f9aa4c19dee4027a4239b52a2e` |

## UX And Accessibility Coverage

Only version/docs metadata changes; no new UI controls, styles or deletion flows. Existing Studio/public/widget presentation and en/vi semantics remain unchanged. Earlier feature screenshots stay outside Git; there are no new evidence images/archives in this PR.

## Defects

No product defect or blocking local acceptance failure. An npm cache permission issue was handled with a task-local cache; no global cache ownership/permissions were changed. All package outputs use temporary paths.

## Gaps Or Untested Areas

Local migration/restore is SQLite; PostgreSQL/Redis/MinIO/image/full browser matrices are exact-head CI gates. No real vendor/customer data, production backup restore, native/device or registry publication claim. Registry availability must be rechecked at actual release time.

## Residual Risk

A version bump prepares source/install pins before registry publication; stable install availability follows the owner-authorised release, not this Draft PR. Existing integrations require operator credentials/setup, unknown external outcomes stay blocked and chat revisions can repeat intentional external effects. Native remains deferred and REQ-0082 remains incomplete.

## Assumptions

The owner approved preparing shared 0.11.0 after merging edit/regenerate. TypeScript/React keep independent versions. Release/main merge, tags, uploads and deployment need explicit release instructions on the validated candidate.

## Required Follow-Up

Wait for exact-head CI, present the same Draft PR for owner implementation/merge acceptance, then perform release/publication only when explicitly instructed. No standalone lifecycle-only PR.

## QA Decision

Local acceptance passes with no blocking failure. Exact-head CI and owner acceptance remain gates; keep task in review/Draft and do not claim a published 0.11.0 release or completed native requirements.

## Final Version Audit

PR #294 also aligns examples/chat-host/README.md with 0.11.0 and independent npm versions. Remaining 0.10.2 references outside lockfiles/Factory history are historical roadmap/release entries. This documentation-only follow-up changes no runtime/package build input, so the passed full profile and artifact receipts remain applicable; exact final-head CI gates delivery.

## Owner Acceptance And Remote CI

Reviewed head e8b2112990b8869b83f029e04be2a8440d16fadc passed 22 checks: full CI 41665808750 (SQLite/Postgres/Redis/MinIO, three browser shards, React 18/19, SDK/runtime matrices), Factory 41665808411, strict handbook 41665808446, image smoke/Trivy 41665808202 and CLI 41665808230. The two skipped jobs are expected PR-only handbook deploy and GHCR publish. This closes the earlier remote-validation gap.

Owner instructed “Release it” on the concrete 0.11.0 candidate; implementation/merge and release/main/tag/registry publication are now authorised. TASK-0238 is done for final one-commit Ready delivery on #294. Finalisation changes only Factory/roadmap lifecycle records; existing local full 8/8, package build/install and backup/restore evidence remains applicable. Wait for fresh exact-head CI before merge. Actual release workflows/registries must be checked; no publication/deployment success is claimed by this acceptance record. Native remains deferred.
