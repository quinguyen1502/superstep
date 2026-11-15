# Task

## Metadata

- Project: superstep
- Task ID: TASK-0283
- Title: Refresh the README and handbook screenshots
- Status: done
- Owner: Thái Quí Nguyễn
- Created: 2026-11-09
- Updated: 2026-11-14
- Requirement IDs:
- Design IDs:
- Architecture IDs:
- Size: S

## Objective

Replace the README and handbook screenshots that no longer match the Studio UI or the text around them, with captures of the running Studio. Keep every image path.

## Scope

### In Scope

- PNGs under `handbook/docs/en/images/` that the README and the English handbook embed, and their copies under `handbook/docs/vi/images/` (English UI for both editions).
- The capture specs `frontend/e2e/handbook.spec.ts` and `frontend/e2e/quickstart.spec.ts`, so the shots stay reproducible with the current editor.
- Captions and steps that no longer match the new shots.

### Out Of Scope

- Product source changes.
- Screenshots of external clients (Telegram, Slack, Google Drive).

## Acceptance Criteria

- Every refreshed image shows the current UI in English: Import repo on the workflow list, the General/Settings/Data/Execution config tabs, the Node palette/State schema tabs, the version footer, top-aligned alert icons.
- The Telegram expense image shows the English example input and an English trace.
- The browser connection image shows the tool list that discovery returns now (six usable tools, upload/download/evaluate listed as off).
- README, README.vi and the handbook still point at existing files; no image is added or removed.
- `HANDBOOK_SHOTS=1` runs of the handbook and quickstart capture specs pass.

## Validation Plan

- `HANDBOOK_SHOTS=1 npx playwright test e2e/handbook.spec.ts e2e/quickstart.spec.ts -g " en"`.
- `REVIEW_SHOTS` runs of the managed tool, attachment, hand-off and expense specs for the shots those specs produce.
- `python3 scripts/check-browser-handbook.py`, `factory validate --only hygiene`, `factory pr check`.

## Results

- 57 of the 58 handbook images were refreshed; `agent-handoffs.png` is pixel-identical to a new capture and stays.
- The 57 refreshed images were copied to the matching `handbook/docs/vi/images/` paths.
- Capture environment: temporary SQLite, mock model, `STUDIO_ENABLE_BROWSER=1` with the browser runtime off, Code nodes on with the remote sandbox service (`python -m app.sandbox_service`) because Docker is not available on the capture machine, browser time zone UTC.
- The managed Google Drive, HTTP API and Slack action shots and the expense trace use the repository's local fixtures and synthetic settings, as before.

## Activity Log

- 2026-11-09: Owner asked to replace the outdated README and handbook screenshots (pt268u). Branch `factory/task-0283-handbook-screenshots` from `develop` at `86715d2c`.
- 2026-11-09: Capture specs updated for the tabbed Config and left panels; added the Chat settings shot and the browser connection and URL source shots. Quickstart and browser guide steps updated in en and vi.

## Integration

- Merged into develop via PR #347 at `f8c76fba`. The lifecycle was reconciled on 2026-11-14.

## Review and QA History

- Review: [Merged PR #347](https://github.com/quinguyen1502/superstep/pull/347) contains the delivered scope and merge history. No separate review artifact was recorded.
- QA: The original PR records the screenshot capture specs and successful handbook, quickstart, and supporting capture runs. See the validation section of the merged PR.

## Handoff Notes

- Branch `factory/task-0283-handbook-screenshots`. Do not merge without the owner.
