# MCP servers

## Managed connections

Under **Settings → MCP**, add a **Managed connection** and choose its service
adapter. Press **Discover tools**, then select it in the existing **MCP tool**
node or an Agent's MCP tool slot. Service-specific behavior stays in adapters;
the graph uses the same tool interface as remote MCP servers.

| Adapter | Connection settings | Tool arguments |
| --- | --- | --- |
| Telegram actions | An existing Telegram channel connection; fixed destination chat ID | `send_message`: plain `text`, optional integer `reply_to_message_id` |
| Google Sheets | Fixed spreadsheet ID and tab name; number of data columns (1–25); encrypted service-account JSON key | `append_row`: `values`, exactly the configured number of scalar values |

Create a [Google service account](https://developers.google.com/identity/protocols/oauth2/service-account),
enable the Sheets API and share the selected spreadsheet with its email as an
editor. Paste its JSON key in Settings. No end-user OAuth or domain-wide
delegation is needed for a directly shared sheet. Secrets are encrypted and
never returned in tool metadata/workflow JSON. Telegram reuses the channel's
secret; another user's personal channel cannot be delegated by choosing it in
an organisation MCP connection. Access and organisation policy are rechecked
at call time.

For six data columns, create headers in A–F and reserve G for the operation ID.
Do not remove or overwrite that column. The [Sheets append API](https://developers.google.com/workspace/sheets/api/reference/rest/v4/spreadsheets.values/append)
receives `RAW` values: strings stay text, including formula-looking input, and
numbers remain numbers. The extra ID allows a read-only lookup after a lost
response. Reconciliation scans at most 100,000 rows; use a new tab before that
limit. Do not share the same tab with writers that alter/remove operation IDs.

### Write outcomes and recovery

Every managed write requires the workflow's stable operation key. Studio stores
an intent before calling the provider. A confirmed result is reused for the
same run/node/iteration; changed arguments or destinations are refused. MCP
nodes also participate in the existing result ledger and worker fencing.

**Recent operations** on the connection shows pending, confirmed, rejected and
unknown results, with the external operation ID. **Check external result** only
reads: Sheets can confirm a matching operation ID, but a missing row is never
permission to append again. A crash before the request can conservatively leave
an unresolved intent. Telegram cannot look up a sent message by this ID, so an
uncertain send stays blocked. Never start a new run merely to bypass an unknown
result; inspect the external service first. Restore the original destination
settings before reconciling an old operation. Rotating credentials can keep
those settings unchanged.

Only a **confirmed** write may lead to a success reply. A provider rejection or
unknown outcome stops a normal MCP node. Agent tools receive the normal tool
error; an Agent's instructions must require confirmation before claiming success.
Workflow tests and mock-model runs perform a dry run without external sends,
writes, token exchanges or intent records. HTTP/stdio MCP behavior is unchanged.
Standalone Python/TypeScript export explicitly refuses managed connections,
because their operation tracking currently requires Studio. Portable templates
contain blank resource references; bind connections after creating a workflow.

[Model Context Protocol](https://modelcontextprotocol.io) servers expose
tools. Register a server once, then call its tools from
[MCP tool](nodes.md#mcp-tool) nodes.

![MCP servers](../images/settings-mcp.png)

## Before you begin

- The `admin` or `editor` role for a personal server. Organisation servers
  and stdio commands need an admin.
- A server that speaks Streamable HTTP, or, for stdio, `STUDIO_MCP_STDIO=1`
  on the API host.

## Register a server

Open **Settings → MCP servers** and choose **Add MCP server**.

=== "Streamable HTTP"

    A URL and optional secret headers. The URL must be public; the connection
    is pinned to the checked IP. Private and loopback addresses (a sidecar
    container, for example) need `STUDIO_MCP_ALLOW_PRIVATE=1`.

=== "stdio"

    A command, its arguments (one per line) and secret environment variables, run as a child process of the API. Stdio is
    off until `STUDIO_MCP_STDIO=1`, and only an admin can register a command.
    The process gets a clean environment, an empty temporary home and
    `STUDIO_MCP_TIMEOUT` seconds (default 30), then its whole process group is
    killed.

    !!! warning
        That is not a sandbox. Run untrusted MCP servers as their own HTTP
        container instead.

**Discover tools** lists what the server offers. Scope is personal or
organisation; admins choose which roles may use organisation servers.
Secrets are encrypted, and the API returns only names and masked values.

## Call a tool

In an MCP tool node pick the server and the tool; the tool's description appears
in the config. Argument strings are
[templates](state.md#references). An argument that is exactly one reference
keeps its type. The result goes to `output_field`.

A shared workflow runs with the **owner's** MCP servers.

To let MCP clients call **your** workflows as tools, see [Workflows as MCP tools](../run/mcp-server.md).

## MCP node or Agent node

An MCP tool node calls one tool with arguments you fill in, at a fixed place
in the graph. To let a model decide whether and when to call a tool, and with
which arguments, add the tool to an [Agent node](agent.md) instead: pick the
server and the tool, and the model reads the tool's description and input
schema from the server. Only the tools you add are offered, never the server's
whole list.
