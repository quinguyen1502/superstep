---
title: Superstep documentation
hide:
  - navigation
  - toc
---

<div class="home" markdown>

# Superstep documentation

Superstep is a self-hosted platform for building LangGraph workflows in
the browser and running them as services. A workflow is a JSON document: the
FastAPI backend validates it, compiles it into a LangGraph `StateGraph`, and
runs it with per-node events. The same workflow can be started over HTTP, on a
cron schedule, or paused for a human decision.

<video id="video" class="home-video" controls playsinline preload="none" poster="assets/video/studio-intro-en.jpg" aria-label="Quickstart video: build, run, approve and trigger a workflow, then the Agent node, time travel, MCP tools and the phone layout">
  <source src="assets/video/studio-intro-en.mp4" type="video/mp4">
</video>

## Quickstart

```bash
git clone https://github.com/quinguyen1502/superstep.git
cd superstep && ./dev.sh
```

Open <http://localhost:5173> and create an account with **Sign up**. LLM nodes answer from an offline mock until you add a model
credential, so nothing else is needed to follow the
[quickstart](start/quickstart.md): build a workflow, run it, approve it, and
call it over HTTP in about ten minutes.

## Explore the docs

<div class="grid cards" markdown>

-   :material-rocket-launch-outline:{ .lg .middle } **Get started**

    ---

    [Overview](start/index.md) · [Quickstart](start/quickstart.md) ·
    [Install](start/install.md) · [Concepts](start/concepts.md)

-   :material-vector-polyline:{ .lg .middle } **Build**

    ---

    [Editor](guide/editor.md) · [Nodes](guide/nodes.md) ·
    [State and references](guide/state.md) · [Code mode](guide/code-mode.md) ·
    [Knowledge bases](guide/knowledge.md) · [MCP servers](guide/mcp.md) ·
    [Templates](guide/templates.md) · [Versions](guide/versions.md)

-   :material-play-circle-outline:{ .lg .middle } **Run**

    ---

    [Runs and traces](run/traces.md) · [Human approval](run/human-approval.md) ·
    [API triggers and webhooks](run/api-triggers.md) · [Schedules](run/schedules.md)

-   :material-server-outline:{ .lg .middle } **Operate**

    ---

    [Deploy with Compose](operate/deploy.md) · [Accounts](operate/accounts.md) ·
    [Roles and sharing](operate/access.md) · [LLM providers](operate/providers.md) ·
    [Approval channels](operate/channels.md) · [Code runtime](operate/code-runtime.md) ·
    [Observability](operate/observability.md) · [Import a repo](operate/import.md)

-   :material-book-open-variant:{ .lg .middle } **Reference**

    ---

    [Configuration](reference/configuration.md) · [HTTP API](reference/api.md) ·
    [Error codes](reference/errors.md) · [Architecture](reference/architecture.md) ·
    [Shortcuts](reference/shortcuts.md) · [Development](reference/development.md) ·
    [FAQ](reference/faq.md)

</div>

## Components

| Part | Built on | Role |
| --- | --- | --- |
| Editor | React, React Flow, shadcn/ui | Draws the graph and writes the workflow JSON; streams run events over WebSocket |
| API | FastAPI, SQLAlchemy, Alembic | Stores workflows and versions, validates and compiles them, serves REST and WebSocket |
| Engine | LangGraph `StateGraph` | Runs the graph in supersteps and checkpoints the state after each one |
| Worker | In-memory queue or Redis | Runs API-triggered, scheduled and recovered runs, and webhook deliveries |
| Storage | SQLite, or Postgres with pgvector | Workflows, runs, checkpoints, credentials and knowledge-base vectors |
| Sandbox | Docker | Python in Tool nodes and imported LangGraph repos |
| Telemetry | OpenTelemetry | One trace per run and one span per node, to OTLP or LangSmith |

See [Architecture](reference/architecture.md) for the request paths and the
guarantees around retries and recovery.

</div>
