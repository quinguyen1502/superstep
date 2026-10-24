# Task

## Metadata

- Project: superstep
- Task ID: TASK-0093
- Status: review (PR)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Requirement IDs: REQ-0055
- Design IDs: none
- Architecture IDs: none

## Objective

Backfill factory records for work merged outside the factory workflow, and verify develop.

## Backfilled

| PR | Title | Merged | Merge commit | Task | Requirement | Review / QA | CI at merge |
| --- | --- | --- | --- | --- | --- | --- | --- |
| [#57](https://github.com/quinguyen1502/superstep/pull/57) | UI polish: tooltips, shortcut keys, history columns, extra Start/End | 2026-10-19 | `0201b47` | TASK-0094 | REQ-0056 | REV-0086 / QA-0086 | failed checks at merge |
| [#65](https://github.com/quinguyen1502/superstep/pull/65) | Handbook on Zensical, platform-style README, and a quickstart video | 2026-10-19 | `a9c0e38` | TASK-0095 | REQ-0057 | REV-0087 / QA-0087 | failed checks at merge |
| [#102](https://github.com/quinguyen1502/superstep/pull/102) | Version 0.3.0 | 2026-10-22 | `af83afb` | TASK-0096 | REQ-0040, REQ-0041, REQ-0042, REQ-0043, REQ-0044 | REV-0088 / QA-0088 | pass |
| [#104](https://github.com/quinguyen1502/superstep/pull/104) | Editor polish: focus ring, quoted node names, split left panel, Add node | 2026-10-22 | `e899c36` | TASK-0097 | REQ-0058 | REV-0089 / QA-0089 | pass |
| [#105](https://github.com/quinguyen1502/superstep/pull/105) | Version 0.3.1: editor polish (#104), MIT license | 2026-10-22 | `fce215b` | TASK-0098 | REQ-0058 | REV-0090 / QA-0090 | pass |
| [#108](https://github.com/quinguyen1502/superstep/pull/108) | feat(brand): Superstep Step-up logo, favicons and brand tokens (DEC-0047) | 2026-10-23 | `387adad` | TASK-0099 | REQ-0059 | REV-0091 / QA-0091 | pass |
| [#114](https://github.com/quinguyen1502/superstep/pull/114) | Version 0.4.0 | 2026-10-23 | `dd12c70` | TASK-0100 | REQ-0045, REQ-0046, REQ-0047, REQ-0059 | REV-0092 / QA-0092 | pass |
| [#119](https://github.com/quinguyen1502/superstep/pull/119) | feat(deploy): all-in-one image and one-click PaaS deploys (Phase 1) | 2026-10-24 | `b2ac4b0` | TASK-0101 | REQ-0060 | REV-0093 / QA-0093 | pass |
| [#120](https://github.com/quinguyen1502/superstep/pull/120) | feat(deploy): Fly.io, DigitalOcean, Koyeb, Zeabur, Northflank, self-hosted guide (Phase 2) | 2026-10-24 | `d7eb8b3` | TASK-0102 | REQ-0060 | REV-0094 / QA-0094 | pass |
| [#121](https://github.com/quinguyen1502/superstep/pull/121) | feat(code): remote sandbox service for Code nodes (PaaS Phase 3) | 2026-10-24 | `008b027` | TASK-0103 | REQ-0060 | REV-0095 / QA-0095 | pass |
| [#122](https://github.com/quinguyen1502/superstep/pull/122) | feat(demo): public demo mode and live demo on Render | 2026-10-24 | `ebc5426` | TASK-0104 | REQ-0061 | REV-0096 / QA-0096 | pass |
| [#123](https://github.com/quinguyen1502/superstep/pull/123) | Version 0.5.0 | 2026-10-24 | `78cbcaa` | TASK-0105 | REQ-0048, REQ-0049, REQ-0060, REQ-0061 | REV-0097 / QA-0097 | pass |
| [#124](https://github.com/quinguyen1502/superstep/pull/124) | fix: v0.5.0 polish (top bar, demo errors, rate-limit test, README captions) | 2026-10-24 | `4dd2d85` | TASK-0106 | REQ-0062 | REV-0098 / QA-0098 | pass |
| [#126](https://github.com/quinguyen1502/superstep/pull/126) | fix(demo): locale-aware mock replies and per-visitor demo history | 2026-10-24 | `74ab1f8` | TASK-0107 | REQ-0063 | REV-0099 / QA-0099 | pass |
| [#127](https://github.com/quinguyen1502/superstep/pull/127) | Public API contract, Python and TypeScript SDKs, handbook guide and reference | 2026-10-24 | `1504fc6` | TASK-0108 | REQ-0064 | REV-0100 / QA-0100 | pass |

## Not backfilled

- Already covered (merged since 2026-10-16 with factory records): every `factory/task-*` PR (#28-#101, #107, #118), #82 (REQ-0040), #85 (REQ-0041), #109-#112 (TASK-0079-0082), #113 (TASK-0083), #116-#117 (TASK-0084/0085).
- Release PRs from develop into main (#46, #67, #75, #79, #81, #103, #106, #115, #125) promote already-recorded work and get no task by practice; #81 carried TASK-0062 (#80).
- Not merged yet (records on their own branches): #128 TASK-0090, #129 TASK-0091, #132 TASK-0087, #133 TASK-0088, #134 TASK-0089; #130 and #131 are superseded by #132 and #133 (owner to decide whether to close).

## ID allocation

- IDs on unmerged branches were reserved by hand because `factory ids next` only sees one working tree: TASK-0087-0089 / REQ-0050-0052 / DEC-0056-0057 / REV, QA-0080-0082 (#132-#134), TASK-0090-0091 / REQ-0053-0054 / DEC-0058-0059 / REV, QA-0083-0084 (#128, #129). This branch: TASK-0092 (todo), TASK-0093, TASK-0094-0108, REQ-0055-0064, REV/QA-0085-0100.

## Activity Log

- 2026-10-24: audited merged PRs since 2026-10-16 (`gh pr list --state merged`), backfilled 15 PRs, added review/QA references to 11 older done tasks, recorded TASK-0092, ran deps apply, verify and validate (QA-0085).

## Handoff Notes

- Review REV-0085, QA-0085.
