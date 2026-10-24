# Task

## Metadata

- Project: superstep
- Task ID: TASK-0095
- Status: done (backfilled)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-24
- Requirement IDs: REQ-0057
- Design IDs: none
- Architecture IDs: none
- Pull request: [#65](https://github.com/quinguyen1502/superstep/pull/65) `docs/handbook-and-intro-video`
- Merge commit: `a9c0e38808749561543c44013e7fb8219872a80d` (2026-10-19)

## Objective

Handbook on Zensical, platform-style README and quickstart video.

> Backfilled 2026-10-24 (TASK-0093): reconstructed from the PR description and diff after the fact; the work was merged outside the factory workflow, so no task, review or QA record existed at the time.

## Scope (from the PR)

- **Handbook (`handbook/`) on [Zensical](https://zensical.org)**, English at `/` and Vietnamese at `/vi/`. Zensical does not support `mkdocs-static-i18n`, so `docs/en/` and `docs/vi/` are two builds of the same page tree (`mkdocs.yml`, `mkdocs.vi.yml` on top of `mkdocs.base.yml`). `lang-switch.js` points the language selector at the same page.
- **Docs written like other platform docs:** the home page is a docs index (definition, video, quickstart commands, section cards, components table). *Quickstart* follows the n8n/Temporal pattern: goal, prerequisites, numbered steps with checks, what you learned, next steps. Install has troubleshooting; API triggers, schedules, knowledge bases and MCP list the roles they need under *Before you begin*.
- **Quickstart video (87 s, en and vi):** `frontend/e2e/quickstart.spec.ts` does the quickstart in the real UI (drag nodes, wire, configure, run, approve, create a token, call the API, schedule, history) and records a frame per step plus the box of every control. `scripts/promo/video.html` moves a cursor to those boxes, with camera zooms, a chapter rail and captions.
- **README / README.vi:** badges, definition, quick start, features, how it works (mermaid), docs, development, contributing.
- **CI (`handbook.yml`):** both trees have the same pages, strict build of both sites, images and videos exist; publishes to GitHub Pages from `main`.
- `zensical build` and `zensical build -f mkdocs.vi.yml`: no issues (strict: links and anchors).
- `python3 check_images.py site`: all images found.
- `HANDBOOK_SHOTS=1 npx playwright test quickstart`: en and vi pass.
- oxlint and tsc clean on the specs. CI does not run (Actions quota).

## Changed files

- 100 files: `.claude/launch.json`, `.github/workflows/handbook.yml`, `README.md`, `README.vi.md`, `docs/api-errors.md`, `frontend/e2e/handbook.spec.ts`, `frontend/e2e/quickstart.spec.ts`, `frontend/src/locales/en.json`, `frontend/src/locales/vi.json`, `handbook/.gitignore`, `handbook/README.md`, `handbook/check_images.py`, `handbook/docs/en/assets/logo.svg`, `handbook/docs/en/assets/video/studio-intro-en.jpg`, `handbook/docs/en/assets/video/studio-intro-en.mp4`, `handbook/docs/en/guide/code-mode.md`, `handbook/docs/en/guide/editor.md`, `handbook/docs/en/guide/index.md`, `handbook/docs/en/guide/knowledge.md`, `handbook/docs/en/guide/mcp.md`, `handbook/docs/en/guide/nodes.md`, `handbook/docs/en/guide/state.md`, `handbook/docs/en/guide/templates.md`, `handbook/docs/en/guide/versions.md`, `handbook/docs/en/images/api-trigger.png` and more.

## Activity Log

- 2026-10-19: merged into develop (a9c0e38).
- 2026-10-24: task record backfilled (TASK-0093); verified retroactively on develop by QA-0085.

## Handoff Notes

- Review REV-0087, QA QA-0087 (retroactive records).
