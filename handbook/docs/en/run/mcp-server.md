# Workflows as MCP tools

Superstep is an MCP server too. Turn it on for a workflow and MCP clients such
as Claude Desktop, Cursor, Claude Code or other agents can call the workflow as
a tool. This is the other direction from [MCP servers](../guide/mcp.md), where
your workflows call tools of servers you add.

## Turn it on

1. Open the workflow, then **More > API**.
2. On **Tokens**, create a token. Clients authenticate with it, exactly as with
   the [public API](public-api.md).
3. On **MCP**, switch on **Expose as an MCP tool**. It is off for every
   workflow until you turn it on, and only people who may manage the
   workflow's tokens can change it.
4. Pick your client and copy the config. Right after you create a token, the
   snippet already contains it; otherwise replace `<token>`.

The server is at `https://<your studio>/mcp` (Streamable HTTP, JSON responses,
no session). Send the token as `Authorization: Bearer wft_...` or
`X-Workflow-Token: wft_...`.

```json title=".cursor/mcp.json"
{
  "mcpServers": {
    "superstep-refunds": {
      "url": "https://superstep.example.com/mcp",
      "headers": { "Authorization": "Bearer wft_..." }
    }
  }
}
```

Claude Desktop starts local servers only, so its config runs `mcp-remote` to
reach the HTTP server; Claude Code takes the URL directly:

```bash
claude mcp add --transport http superstep-refunds https://superstep.example.com/mcp \
  --header "Authorization: Bearer wft_..."
```

## Tools

A token belongs to one workflow, so a client sees three tools:

| Tool | What it does |
| --- | --- |
| `run_<workflow name>` | Runs the latest saved version. Its input schema is the workflow's state fields; the arguments are the run's input. Returns the run result: `status`, `final_state`, `error`, `waiting`, `metrics`. |
| `get_run` | Status and result of a run (`run_id`). |
| `resume_run` | Answers the Human node a waiting run is paused at (`run_id`, `response`: text, or `true` / `false` to approve / reject) and waits for the run to settle again. |

Runs are ordinary API runs: they show in the workflow's history with source
API, count against the token's rate limit (`STUDIO_TRIGGER_RATE_LIMIT`) and
use the same input checks. A tool call waits up to `STUDIO_SYNC_WAIT_MAX`
seconds; a run still going then returns `status: running` and its `run_id`,
so the client polls `get_run`.

### Human nodes

A run that reaches a Human node returns `status: waiting` with its `run_id`
and the node's prompt under `waiting`. The client (or the person using it)
answers with `resume_run`; the run continues from its checkpoint. People can
also answer it in Superstep, in the editor or the inbox, as with any waiting
run.

### Errors

Failures come back as tool errors (`isError: true`) whose content is the
common error object, for example `{"error": {"code": "RUN_NOT_WAITING", ...}}`.
Requests without a valid token are refused before MCP with
`401 TRIGGER_TOKEN_INVALID`; a workflow that is not turned on answers
`403 MCP_SERVER_DISABLED`.

## Demo mode

In the public demo the visitor account cannot create tokens or change
settings, so it cannot expose a workflow.
