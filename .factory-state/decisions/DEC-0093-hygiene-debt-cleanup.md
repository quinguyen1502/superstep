# Decision

- Decision ID: DEC-0093
- Project: superstep
- Status: implementation direction within owner-authorised REQ-0093 (pt267u: clean up the hygiene debt)
- Created/Updated: 2026-11-09
- Related: REQ-0093, DEC-0092, TASK-0282

## Decision

Vietnamese text lives only in real locale catalogs, and every test, doc and artifact outside them is English or reads the Vietnamese from a catalog:

- Backend user-facing copy (chat-channel messages, the approval and browser ask texts, attachment labels, the offline mock answer and classifier keywords, the sample order tool text and the embedding stop words) moves to `backend/app/locales/en.json` and `vi.json`, read through `app/engine/locale.py` (`catalog`, `text`, `by_locale`) and shipped as package data. Behaviour is unchanged.
- The React Native package and example app keep their labels in `src/locales/en.json` and `vi.json` next to `labels.ts`.
- The promo video captions move to `scripts/promo/locales/en.json` and `vi.json`; `render.mjs` injects them.
- The Vietnamese glossary moves from `docs/ui-conventions.md` rule 10 to `frontend/src/locales/vi-glossary.md`, beside the catalog it governs.
- Backend tests read Vietnamese expectations through `app.engine.locale.text`, SDK tests through `Catalog.load("vi")`, frontend unit tests through `i18n.t` or the imported catalog, and Playwright specs through `frontend/e2e/catalog.ts` (`vt`, `st`, `vin`). Vietnamese test inputs that are not UI copy live in `frontend/e2e/fixtures/inputs.vi.json`.
- Sample data that only needs non-ASCII text (token vectors, upper-casing, slugs, file names) uses non-Vietnamese accented text.
- `.factory-state/` artifacts quote the owner's instructions in English translation; the owner's name stays allowed through `hygiene.yaml`.
- `.factory-state/hygiene.yaml` keeps no `i18n_paths` or `skip_paths`. Every allowed path comes from the checker's built-in locale rules (a `locales` directory or a `vi` file name).
- CI runs `factory validate --only hygiene` in `factory-verify.yml` and `factory pr check` in `factory-pr-text.yml`.

## Alternatives considered

- List the React Native `labels.ts` files under `i18n_paths`: rejected; JSON catalogs follow the same rule as the rest of the repository and need no exception.
- Loosen e2e assertions to patterns: rejected; tests keep exact expectations read from the catalogs.
