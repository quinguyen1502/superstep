# Decision

- Decision ID: DEC-0091
- Project: superstep
- Status: implementation direction within owner-authorised REQ-0092
- Created/Updated: 2026-11-09
- Related: REQ-0092, PLAN-0012, DEC-0085

## Decision

Enable the browser **feature / discovery gate** by default using the same convention as `STUDIO_WORKER` / `recover_on_start`:

```python
os.environ.get("STUDIO_ENABLE_BROWSER", "1") != "0"
```

Keep `STUDIO_ENABLE_BROWSER_RUNTIME` opt-in (`== "1"`) so trusted runs still do not drive Chromium until an operator sets that env.

Connection-level product defaults from DEC-0085 stay unchanged (required non-empty whitelist; mutating approval off; allow_evaluate_js / allow_upload / allow_download false; web tools default `fetch` only).

## Alternatives considered

- Also defaulting the runtime gate on: rejected by the owner (runs must not drive a browser until runtime is set).
- Flipping connection `allow_*` toggles: rejected; owner asked for feature gate only.

## Amendment 2026-11-09 (UX visibility)

Advertise all first-delivery browser tools in discovery even when `allow_*` is false; append an explicit disabled note. Enforce allow_* and runtime at execution time. Expose `browser_runtime_enabled` on the MCP list payload so Settings can show a runtime-off banner with a handbook link (`guide/browser`). Connection toggles stay default false; whitelist still required.
