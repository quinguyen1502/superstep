# Task

## Metadata

- Project: superstep
- Task ID: TASK-0122
- Status: review
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: none (owner request in chat, 2026-10-26: remake the intro video with the new features)
- Design IDs: none
- Architecture IDs: none

## Objective

Bring the handbook home page video (en, vi) up to date: the current editor (Config tabs, TASK-0121) and the features
added since it was made (Agent node, time travel, workflows as MCP tools, phone layout).

## Scope

### In Scope

- `frontend/e2e/quickstart.spec.ts` (run with `HANDBOOK_SHOTS=1`):
  - chapter 3 frames follow the Config tabs: `llm-prompt` (prompt on Settings), then `llm-config` (output field on Data);
  - new chapter 6 frames: `gallery-agent`, `agent`, `agent-waiting`, `agent-trace`, `time-travel`, `mcp`, and two
    390x844 screenshots, `phone-canvas` and `phone-config`, taken in a second browser context with the same session;
  - the Support agent template's policy search tool needs a knowledge base before the workflow runs: the spec creates
    one (`Refund policy` / `Chính sách hoàn tiền`) and picks it for that tool through the API.
- `scripts/promo/video.html`:
  - a click on the Data tab in chapter 3, and the Data tab in the output caption;
  - chapter 6, New / Mới, with seven captions;
  - a phone frame over a dimmed window;
  - the outro moved; 127.2 s at 1x, so 90.9 s at SPEED 1.4.
- `scripts/promo/music.mjs`: section times and length follow the new timeline.
- Outputs:
  - videos and posters `handbook/docs/<lang>/assets/video/studio-intro-<lang>.{mp4,jpg}`;
  - the quickstart screenshots `handbook/docs/<lang>/images/quickstart-*.png`, recaptured by the spec.
- The video's `aria-label` on the handbook home pages, `scripts/promo/README.md`, `CHANGELOG.md`.

### Out Of Scope

- The Support agent template itself (it cannot run until a knowledge base is picked for its policy tool; noted below).

## Acceptance Criteria

- The quickstart spec passes in en and vi and writes every frame the timeline uses (render.mjs refuses missing images).
- Stills in both languages: captions fit on one line, the rail shows six chapters, the camera and cursor land on the
  controls named in the captions.
- Both MP4s render at 1920x1080, 30 fps, with the music bed, and play to the end card.

## Validation

- `HANDBOOK_SHOTS=1 npx playwright test quickstart` (e2e ports 8150/5230/8151/8152): 2 passed.
- `node render.mjs --lang en --stills …` and `--lang vi --stills …`: checked as contact sheets.
- `node render.mjs --lang en`, `node render.mjs --lang vi`: see the PR for duration and size.

## Notes

- The Support agent template, used as is, fails on Run with WORKFLOW_INVALID ("tool search_refund_policy: choose a
  knowledge base"). The template's test cases and `agent-tests.spec.ts` remove that tool first. A follow-up could
  make a template's empty knowledge base a warning, or ship the template without that tool.
