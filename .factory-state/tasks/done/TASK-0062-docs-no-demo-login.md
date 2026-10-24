# Task

## Metadata

- Project: superstep
- Task ID: TASK-0062
- Status: done (PR #80)
- Phase: release
- Owner: Thái Quí Nguyễn
- Created: 2026-10-20
- Updated: 2026-10-20
- Requirement IDs: none (a docs change asked for by the owner)
- Design IDs: none
- Architecture IDs: none

## Objective

The docs no longer mention the seeded demo account (`admin@example.com` / `admin123`). They tell the reader to
create an account with **Sign up** instead.

## Changes

- Handbook en and vi:
  - `index.md`: create an account with **Sign up**.
  - `start/install.md`: same. A new account gets the example workflow and the `editor` role. To get an admin, start
    the studio with `STUDIO_ADMIN_EMAILS` set to that e-mail, then sign up.
  - `start/quickstart.md`: the prerequisite is an account; the default `editor` role covers the guide. Checked:
    tokens and schedules need `resources.manage`, which editors have.
- `README.md`, `README.vi.md`: quick start says **Sign up**.

## Out Of Scope

- The demo account itself, and the sign-in page hint that shows it outside production (the frontend's
  `auth.loginHint`).
- Pages that only say production skips the demo account (`operate/deploy.md`, `operate/accounts.md`,
  `reference/configuration.md`). They give no credentials.
- Screenshots. Some settings screenshots show the signed-in e-mail `admin@example.com`, but no password.

## Acceptance Criteria

- No page of the handbook or the READMEs contains `admin@example.com` or `admin123`.
- The handbook builds in both languages.

## Validation

- `git grep "admin123\|admin@example" -- handbook/docs README.md README.vi.md` finds nothing.
- `zensical build` and `zensical build -f mkdocs.vi.yml`: no issues. Neither string appears in the built `site/`.

## Handoff Notes

- Backfilled 2026-10-24 (TASK-0093): Review none recorded at the time; QA none recorded at the time; develop verified retroactively by QA-0085.
