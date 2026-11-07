# Decision

- Decision ID: DEC-0086
- Project: superstep
- Status: Accepted 2026-11-07 — owner chose option A (fixed published handbook links)
- Created/Updated: 2026-11-06
- Related: REQ-0087, DES-0005, PLAN-0007

Studio has no handbook-link helper today; locale strings only say "see the handbook". The handbook is published at `https://quinguyen1502.github.io/superstep/` (en) and `.../superstep/vi/` (vi) per `handbook/mkdocs*.yml`.

Options:

- **A (recommended):** a frontend constant pointing at the published handbook, with `/vi/` for Vietnamese and a page path plus optional anchor. No new environment variable, no backend change. Air-gapped installs see a link that may not load; that is documented.
- **B:** A plus an optional build-time `VITE_HANDBOOK_URL` override for forks/mirrors. Adds a build knob, still no runtime/env change.
- **C:** runtime `STUDIO_DOCS_URL` exposed through an API field. Most flexible, but adds a new server setting and API surface.

Recommendation A keeps scope minimal and matches the current single published handbook; B can follow if a fork needs it.

Outcome: option A accepted by the owner on 2026-11-07. B/C are not implemented.
