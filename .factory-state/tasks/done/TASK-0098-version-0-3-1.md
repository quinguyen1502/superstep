# Task

## Metadata

- Project: superstep
- Task ID: TASK-0098
- Status: done (backfilled)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-22
- Updated: 2026-10-24
- Requirement IDs: REQ-0058
- Design IDs: none
- Architecture IDs: none
- Pull request: [#105](https://github.com/quinguyen1502/superstep/pull/105) `factory/version-0.3.1`
- Merge commit: `fce215b664edb62aaa2bcc41cfe1ff69f79c4891` (2026-10-22)

## Objective

Version 0.3.1 and MIT license.

> Backfilled 2026-10-24 (TASK-0093): reconstructed from the PR description and diff after the fact; the work was merged outside the factory workflow, so no task, review or QA record existed at the time.

## Scope (from the PR)

- **Version 0.3.1** in `backend/pyproject.toml`, `frontend/package.json` and `frontend/package-lock.json`. This release carries the editor polish from #104.
- **`LICENSE`:** the MIT license, `Copyright (c) 2026 Thái Quí Nguyễn`.
- **`backend/pyproject.toml`:** `license = "MIT"`, an SPDX expression. That form needs setuptools 77 or later, so the build requirement moves from `setuptools>=68` to `setuptools>=77`.
- **`frontend/package.json`:** `"license": "MIT"`.
- **`README.md` and `README.vi.md`:** a License / Giấy phép section that links to `LICENSE`.
- `pip wheel .` builds the backend, and the wheel metadata shows `Version: 0.3.1` and `License-Expression: MIT`.
- `package-lock.json` was regenerated with `npm version` and `npm install --package-lock-only`.

## Changed files

- 6 files: `LICENSE`, `README.md`, `README.vi.md`, `backend/pyproject.toml`, `frontend/package-lock.json`, `frontend/package.json`.

## Activity Log

- 2026-10-22: merged into develop (fce215b).
- 2026-10-24: task record backfilled (TASK-0093); verified retroactively on develop by QA-0085.

## Handoff Notes

- Review REV-0090, QA QA-0090 (retroactive records).
