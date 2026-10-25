# MCP servers

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
