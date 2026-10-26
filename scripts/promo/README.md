# Quickstart video

Renders the 91 s video on the handbook home page. Its first five chapters follow the
[Quickstart](../../handbook/docs/en/start/quickstart.md) step by step: create a
blank workflow, drag an LLM and a Human node, wire and configure them (the prompt on the Config **Settings** tab, the
output field on **Data**), send the approval request to Slack, run and approve, read the state diff, create an API
token, call it with `curl`, add a schedule, and open History. A sixth chapter, **New**, shows the Support agent
template's Agent node with an approved tool call and its rounds in the trace, time travel, the workflow as an MCP
tool, and the phone layout.

The screens are real: `frontend/e2e/quickstart.spec.ts` does the quickstart in
the UI and saves one frame per step, plus the box of every control the next
action uses, and two 390x844 screenshots of the editor (`phone-canvas.png`, `phone-config.png`) that the video
shows in a phone frame. `video.html` is an HTML timeline that moves a cursor to those
boxes, zooms the camera onto them and captions each step. Chrome renders it
frame by frame and ffmpeg encodes the frames with a generated music bed.

| Output | Path |
| --- | --- |
| Video and poster | `handbook/docs/<lang>/assets/video/studio-intro-<lang>.{mp4,jpg}` |
| Frames and `flow.json` | `scripts/promo/build/frames/<lang>/` (ignored by git) |

## Requirements

- Node 20 or later and `npm install` in `frontend/` (the spec and the renderer
  use its Playwright).
- Google Chrome, or Playwright's Chromium (`npx playwright install chromium`
  in `frontend/`). Set `CHROME_PATH` for a Chrome in another place.
- `ffmpeg` on `PATH`.
- Network access for the Inter and JetBrains Mono web fonts.

## Render

```bash
cd frontend && HANDBOOK_SHOTS=1 npm run e2e -- quickstart   # frames for en and vi
cd ../scripts/promo
node render.mjs --lang en    # 1920x1080, 30 fps
node render.mjs --lang vi
```

The spec takes about a minute, each render a few minutes. To check a layout
without encoding, render stills at chosen seconds:

```bash
node render.mjs --lang en --stills 9,40,55,75
```

Stills and `renderAt` take seconds of the output video. The script in
`video.html` is written at 1x and played at `SPEED` (1.4): change that one
number to make the whole video faster or slower; `music.mjs` follows it.

To inspect one moment, open `video.html?lang=vi` in Chrome started with
`--allow-file-access-from-files` and call `renderAt(seconds)` in the console.
To use a licensed track instead of the generated bed:
`node render.mjs --lang en --audio path/to/track.m4a`. The track is cut to the
video's length and faded out over the last 3 s.

## Files

| File | Role |
| --- | --- |
| `video.html` | The timeline: the en and vi captions, and the script of frames, cursor moves, clicks, drags, camera moves and the terminal. |
| `render.mjs` | Loads `flow.json`, renders the poster, the frames and the final MP4. |
| `music.mjs` | Synthesises the music bed. Its section times match the timeline. |
| `paths.mjs` | Shared paths and Chrome lookup. |

## Changing the video

The script in `video.html` refers to frames and targets by the names the spec
gives them (`snap('waiting', { approve: … })` → `mid('waiting', 'approve')`).
Add a step in the spec first, then use its frame in the script. A UI change
that moves a control needs only a new spec run: the cursor follows the boxes.
Check both languages with `--stills` after a change, and keep the captions in
line with the quickstart page.
