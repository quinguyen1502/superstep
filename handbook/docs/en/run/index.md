# Run

A workflow runs in six ways. All of them go through the same engine,
produce the same trace, and appear in the run history (**Run → View all**).

| Started by | How | Badge in History |
| --- | --- | --- |
| The editor | **Run**, **Step** or **Run to here**, over `/ws/run` | — |
| Another service | `POST /api/hooks/workflows/{wid}/runs` with a workflow token | **API** |
| An MCP client | The workflow's `run_...` tool at `/mcp`, with a workflow token | **API** |
| A timetable | A cron schedule on the workflow | **Schedule** |
| A chat message | A command word to your Slack app or Telegram bot | **Chat** |
| A person resuming | Approve, reject or answer a waiting Human node | — |

<div class="grid cards" markdown>

-   :material-chart-gantt:{ .lg .middle } **[Runs and traces](traces.md)**

    ---

    The Logs timeline, stepping, cancel, limits and cost.

-   :material-account-check:{ .lg .middle } **[Human approval](human-approval.md)**

    ---

    Waiting runs, notifications and chat approvals.

-   :material-api:{ .lg .middle } **[API triggers and webhooks](api-triggers.md)**

    ---

    Tokens, sync and async runs, signed callbacks, workers.

-   :material-tools:{ .lg .middle } **[Workflows as MCP tools](mcp-server.md)**

    ---

    Claude Desktop, Cursor and other agents call the workflow as a tool.

-   :material-calendar-clock:{ .lg .middle } **[Schedules](schedules.md)**

    ---

    Cron, time zones and missed times.

-   :material-message-text-outline:{ .lg .middle } **[Chat triggers](chat-triggers.md)**

    ---

    A message to the Slack app or Telegram bot starts a run; the bot answers.

-   :material-chat-processing-outline:{ .lg .middle } **[Chat](chat.md)**

    ---

    Chat with a workflow in the studio, with memory and its steps.

-   :material-flask-outline:{ .lg .middle } **[Workflow tests](tests.md)**

    ---

    Test cases, Run all, comparison with earlier versions.

</div>
