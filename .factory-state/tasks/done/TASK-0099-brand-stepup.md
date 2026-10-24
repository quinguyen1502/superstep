# Task

## Metadata

- Project: superstep
- Task ID: TASK-0099
- Status: done (backfilled)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-23
- Updated: 2026-10-24
- Requirement IDs: REQ-0059
- Design IDs: none
- Architecture IDs: DEC-0047
- Pull request: [#108](https://github.com/quinguyen1502/superstep/pull/108) `feat/brand-stepup`
- Merge commit: `387adad484f6a290bfc382c733705f536cb17b0b` (2026-10-23)

## Objective

Superstep Step-up logo, favicons and brand tokens.

> Backfilled 2026-10-24 (TASK-0093): reconstructed from the PR description and diff after the fact; the work was merged outside the factory workflow, so no task, review or QA record existed at the time.

## Scope (from the PR)

- `frontend/public/brand/`: mark (light/dark), mono (`currentColor`), lockups (light/dark/mono) and the wordmark. The "superstep" wordmark is Geist 650 converted to outlines.
- `favicon.svg` now switches with `prefers-color-scheme`. Added 16/32 PNG favicons, `apple-touch-icon.png`, 192/512 icons, `site.webmanifest` and `theme-color` (`index.html`).
- New `components/logo.tsx` (`Logo`, `LogoMark`) built from tokens only: the tile is `fill-primary`, the arrow `stroke-primary-foreground`, the square `fill-brand-accent`. `mono` uses currentColor.
- It replaces the lucide `Workflow` glyph in the Workflows, Editor, Approvals, Settings and login screens.
- light: `--primary oklch(0.21 0.03 285)`, `--primary-foreground oklch(0.985 0 0)` (17.0:1), `--ring oklch(0.41 0.03 285)`
- dark: `--primary oklch(0.93 0.012 285)`, `--primary-foreground oklch(0.21 0.03 285)` (14.5:1), `--ring oklch(0.7 0.02 285)`
- new `--brand-accent` / `--brand-accent-foreground` (light `oklch(0.82 0.15 200)`, dark `oklch(0.55 0.12 215)`), exposed as `--color-brand-accent`. It is decorative only, never a status colour.
- `--sidebar-primary` / `--sidebar-ring` now follow primary/ring (dark mode used to have a stray blue).
- Replaced the handbook logo (en; vi is a symlink to it). The off-system violet `#6c4bd8` / `#a48bff` became ink + teal in `extra.css` and `scripts/promo/video.html`.
- `vi.json` and the READMEs are not touched.

## Changed files

- 29 files: `.factory-state/decisions/DEC-0047-brand-stepup.md`, `README.md`, `README.vi.md`, `frontend/index.html`, `frontend/public/apple-touch-icon.png`, `frontend/public/brand/superstep-lockup-dark.svg`, `frontend/public/brand/superstep-lockup-mono.svg`, `frontend/public/brand/superstep-lockup.svg`, `frontend/public/brand/superstep-mark-dark.svg`, `frontend/public/brand/superstep-mark.svg`, `frontend/public/brand/superstep-mono.svg`, `frontend/public/brand/superstep-wordmark.svg`, `frontend/public/favicon-16.png`, `frontend/public/favicon-32.png`, `frontend/public/favicon.svg`, `frontend/public/icon-192.png`, `frontend/public/icon-512.png`, `frontend/public/site.webmanifest`, `frontend/src/components/__tests__/logo.test.tsx`, `frontend/src/components/editor/editor-header.tsx`, `frontend/src/components/logo.tsx`, `frontend/src/index.css`, `frontend/src/pages/Approvals.tsx`, `frontend/src/pages/Auth.tsx`, `frontend/src/pages/Workflows.tsx` and more.

## Activity Log

- 2026-10-23: merged into develop (387adad).
- 2026-10-24: task record backfilled (TASK-0093); verified retroactively on develop by QA-0085.

## Handoff Notes

- Review REV-0091, QA QA-0091 (retroactive records).
