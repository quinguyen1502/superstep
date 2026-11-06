# Typed browser recipes as workflows

TASK-0248 represents a recipe as an ordinary saved workflow containing a bounded
linear chain of the existing MCP browser actions. It uses existing workflow
versions, workflow-as-tool child runs and MCP exposure. There is no separate
recipe store, canvas node, orchestration language or hidden model loop. The
experimental browser flags and connection/profile/proxy policy still apply.

The [lookup_shipment example](../examples/browser/lookup_shipment.json) accepts
`url` and `order_id` per call and returns only the declared `shipment` extraction.
Its literal target labels are an example layout contract; adapt them to the
reviewed site before use. It is JSON/API metadata until TASK-0249/0250 supplies
the connection/recipe configuration UI. Executable exports remain TASK-0251/0252.

## Definition and invocation

The workflow root adds:

```json
{
  "browser_recipe": {
    "version": 1,
    "connection_id": "browser",
    "inputs": ["url", "order_id"],
    "outputs": ["shipment"]
  }
}
```

`version` is the contract version, an integer 1. The saved workflow revision is
still the existing workflow version. There must be exactly one Start, one End,
1–20 MCP actions and one linear path through every node. No Agent, branching,
loop, subgraph, generic code or per-node retry/cache setting is accepted inside
the recipe. Every action names the fixed connection and one of the six existing
browser operations. Current ownership/feature/connection checks remain mandatory.

Input names select declared primitive workflow state fields. All are required;
unknown arguments are rejected. Strings are nonempty and at most 2,048 characters;
the full finite UTF-8 JSON input is at most 16 KiB. Input values cannot replace
intermediate observations, connection, profile or proxy authority. Outputs select
unique object fields written by recipe actions, at most 20 fields/256 KiB total.
Internal page state and raw input values are omitted from the final recipe result.

Use an existing Agent workflow tool with inputs `url/order_id` and outputs
`shipment`, or enable the saved workflow's normal MCP endpoint. MCP advertises
the closed recipe input schema under `run_lookup_shipment` (the existing workflow
tool naming convention), plus `get_run`/`resume_run`. Generic external MCP nodes
can call that endpoint. Existing workflow access, token/PAT scope and rate rules
apply. Reading a finished result does not call the browser or restore page state.

The parent Agent snapshots the child definition/version during normal planning.
API/MCP queue acceptance also stores the accepted recipe definition and available
workflow revision before enqueue. Editing the saved recipe while it is queued
cannot change its actions; recovery before first progress retains that snapshot.
Workflow deletion or revoked access still prevents execution. Invalid contract
versions return `BROWSER_RECIPE_INVALID`; invalid arguments use the shared
`MCP_ARGUMENT_INVALID` contract and both error locales are present.

## Targets and shared page

All validated recipe MCP actions share one run/principal/connection-scoped group.
Other workflows' standalone MCP nodes retain their independent groups. Compiler
markers are derived from the validated root; client-supplied markers are stripped.
Each action still reserves the normal durable ticket and calls the same worker
handler as autonomous tools. The original connection action/session limits also
apply; a 20-action definition does not increase a smaller configured limit.

Click/fill derive references from an earlier navigate/snapshot result with a
literal target, rather than accepting caller-supplied element IDs:

```json
{
  "target": {"observation_field":"page","role":"textbox","text":"Order ID"},
  "arguments": {"value":"{{state.order_id}}"}
}
```

Extract uses `targets`, mapping each output name to one earlier observation and
literal role/optional text. All fields must use the same observation. Role-only
extraction requires exactly one match; the example uses a semantic `status` role
whose content can vary. Click/fill always require literal text too. Missing or
ambiguous matches stop before an effect. Worker fingerprints/page generations
still reject stale references. These are exact matches on the existing bounded
observation, not CSS/JavaScript/XPath or an adaptive selector/model fallback.
An unchanged unique role does not establish business identity; choose semantic
roles/text and saved origins appropriate to the reviewed site.

After fill/click invalidates references, put a snapshot action before selecting
the next target. A failed/challenged/expired/stale/unknown action stops the recipe;
rejection/expiry remains visible in the error returned to the parent model. The
recipe never switches into an Agent to repair its layout. Mock/test mode yields
typed dry-run action outputs without browser or external traffic.

## Human approval and recovery

Fill and click always use the exact-target durable Human receipt described in
[browser-approvals.md](browser-approvals.md). The existing inbox/channel UI pauses
and resumes the normal run. A generic MCP token's `resume_run("approved")` has no
Human receipt and cannot grant the action. A live verified waiting resume can
retain the same page under a newer fence; its original lifetime does not extend.

Unknown effects close the page and are never replayed. Browser history checks
include workflow-tool descendants, so a parent fork cannot bypass a child's
browser state. Before creating a new recipe child in the same parent run, the
service rejects recorded unknown commands/intents or a failed child after a
consumed possible-effect receipt. Reusing an existing child key can report that
child's outcome; it cannot open a replacement page. This deliberately stops a
parent model's blind fresh-call retry after an uncertain recipe. It is not a
promise of exactly-once website writes or undoing a dispatched effect.

Recipes are workflows, so their deletion uses the existing shared exact-name
workflow confirmation and DELETE API. No separate delete endpoint or approval
exception is introduced.

## Evidence

`tests/test_browser_recipes.py` covers typed bounds, versions, targets, two Human
pauses in one page, different per-call URLs/IDs, declared-only outputs, layout
failure, dry-run, immutable snapshots, existing Agent child slots and real MCP
SDK/server invocation. It proves that a token/model answer cannot grant a browser
receipt and completed-result reads send no additional actions. Recursive history
guards run on SQLite and disposable PostgreSQL 17.

`scripts/test-browser-recipes.py` runs real isolated Chromium against a disposable
site/database. Two calls each execute six ordered actions and two approvals on one
page. A third call injects lost acknowledgment after the fixture POST; outcome is
unknown, with no replacement page/repeat. A changed target stops. Evidence:
three intended POSTs total, zero repeated POSTs, declared-only outputs, and no
screenshots written to Git. It removes its own containers/network/database.
