# Superstep vs n8n, Dify, CrewAI and PydanticAI

Teams choosing a tool for AI workflows often look at n8n, Dify, CrewAI and
PydanticAI next to Superstep. They overlap, but each is built around a
different idea: n8n is a general automation platform, Dify an LLM app
platform, CrewAI and PydanticAI Python frameworks. This page compares them
fairly so you can pick the right one, or combine them. Facts about the other
products come from their own documentation, sites and license files (listed
under [Sources](#sources)) as checked on 25 October 2026; features, plans and
licenses can change, so check those pages before you decide. For LangSmith,
see [Superstep vs LangSmith](superstep-vs-langsmith.md).

## In one sentence each

| Product | What it is |
| --- | --- |
| **Superstep** | A visual, self-hosted studio for LangGraph workflows (MIT license), with code export, a LangGraph-compatible API, human-in-the-loop channels and a Vietnamese UI. |
| **n8n** | A workflow automation platform with a visual editor, a large library of app integrations and AI nodes (agents, tools, memory) built on LangChain concepts. |
| **Dify** | An open-source platform for building LLM applications: agents, agentic workflows and chatbots on your own data, published as web apps, APIs or MCP servers. |
| **CrewAI** | An open-source Python framework for multi-agent systems (Crews of role-playing agents inside event-driven Flows), with a commercial platform, CrewAI AMP, that adds deployment, tracing and the no-code Crew Studio. |
| **PydanticAI** | A typed Python agent framework from the Pydantic team, with Pydantic Graph, Pydantic Evals, durable execution integrations and the Logfire observability platform around it. |

## Summary comparison

| | Superstep | n8n | Dify | CrewAI | PydanticAI |
| --- | --- | --- | --- | --- | --- |
| Main approach | Visual graph editor; Code nodes optional | Visual workflow editor; Code node optional | Visual app and workflow builder | Python code; no-code Crew Studio in AMP | Python code; YAML/JSON agent specs |
| Runs on LangGraph | Yes: workflows compile to a LangGraph `StateGraph` | No; AI nodes implement LangChain concepts | No | No (the docs include a guide for moving from LangGraph) | No (has its own Pydantic Graph) |
| License | MIT | Sustainable Use License (source-available, internal and non-commercial use limits); enterprise files under a separate license | Modified Apache 2.0 (no multi-tenant service without permission; keep the logo and copyright in the frontend) | MIT (framework); AMP is commercial | MIT |
| Self-hosting | Yes, free | Yes, Community edition free; paid enterprise plans | Yes, Community Edition with Docker Compose | Framework runs anywhere; AMP is a managed platform | Library runs anywhere; Logfire is a hosted service with a free tier |
| Human in the loop | Human nodes: approve in the studio, Slack, Telegram, WhatsApp, email or Teams, with deadlines | Human review for AI Agent tool calls; Slack "send and wait" approvals | Human Input node pauses a workflow | `@human_feedback` in Flows; resume endpoint in AMP | Human approval of tool calls; long waits through durable engines |
| Durable runs and time travel | Database checkpoints, leased worker jobs, fork a finished run from a checkpoint | Queue mode with workers | Not covered by the sources | `@persist` flow state, restore from a saved state | Durable execution on Temporal, DBOS, Prefect and others; step persistence to save, resume and fork |
| Tests, evals, observability | Workflow tests, LangSmith evals, OpenTelemetry traces | Evaluations (test cases, metrics); OpenTelemetry for self-hosted | Logs, dashboard, annotations; LangSmith, Langfuse, Opik, Phoenix and other integrations | AMP tracing; many third-party integrations | Pydantic Evals; OpenTelemetry-native, Logfire |
| API and SDK | Public run API, Python `superstep` and TypeScript `@superstep/sdk` SDKs, Agent Server API subset at `/api/lg` | REST API and webhooks | REST API, `difyctl` CLI, MCP server publishing | Python library; AMP REST API | Python library; AG-UI and Vercel AI streams |
| Code export | Runnable LangGraph Python or LangGraph.js project | No | No | Not applicable (code-first) | Not applicable (code-first) |

## Superstep

- **Visual LangGraph.** Graphs are drawn on a canvas (13 node types, a typed
  state with reducers, loops, parallel branches, subgraphs, Human nodes) and
  compile to a LangGraph `StateGraph`. Python and TypeScript Code nodes run in
  a locked Docker sandbox (on the host on managed platforms) when you need
  code. See [Nodes](../guide/nodes.md).
- **Code export and LangGraph interop.** Any workflow exports as a runnable
  LangGraph project (`langgraph.json`, served by `langgraph dev`, see
  [Export to Python](../guide/python-export.md)), and a subset of the Agent
  Server API at `/api/lg` lets the official `langgraph-sdk` clients run
  workflows (see [LangGraph-compatible API](../run/agent-server-api.md)).
- **Human in the loop where people already are.** Human nodes pause a run from
  a checkpoint; approve in the studio, Slack, Telegram, WhatsApp, email or
  Teams, with reminders, escalation and expiry (see
  [Human approval](../run/human-approval.md)).
- **Reliability and debugging.** Checkpoints in the database, leased worker
  jobs, effectively-once side effects, step-by-step runs and time travel: inspect
  a finished run's checkpoints, edit a state and fork a new run.
- **Tests and traces.** Workflow tests with checks (see
  [Workflow tests](../run/tests.md)), optional LangSmith datasets and
  experiments, OpenTelemetry traces (see [Traces](../run/traces.md)).
- **Services, not only a studio.** API tokens, signed webhooks, cron schedules,
  chat triggers, and a public API with Python and TypeScript SDKs (see
  [Public API and SDKs](../run/public-api.md)).
- **Self-hosted, MIT.** SQLite by default or Postgres with pgvector, optional
  Redis and worker, Docker images on GHCR and one-click PaaS deploys (see
  [Deploy](../operate/deploy.md)). Vietnamese and English UI and handbook.

What Superstep does not try to be: it has far fewer app integrations than n8n
or Dify (it connects through HTTP, MCP servers, email and its chat channels),
no hosted cloud service and no marketplace.

## n8n

n8n is a workflow automation platform: a visual editor that connects apps and
services through integration nodes, triggers and flow logic, with code where
needed. Its AI section lets you connect LLM providers, add agents, tools,
memory, vector stores and MCP servers, and describes how n8n implements
LangChain concepts. AI Agent tools can require human approval (the workflow
pauses and sends the request to Slack, Telegram or n8n Chat), and Evaluations
check AI workflows against test cases and metrics. n8n runs as n8n Cloud or
self-hosted (npm, Docker, Docker Compose, cloud providers), with queue mode for
scaling.

Its license is the Sustainable Use License: you may use or modify the software
"only for your own internal business purposes or for non-commercial or personal
use", and files marked `.ee` need an n8n Enterprise license. It is
source-available, not an OSI open-source license.

Where n8n is strong: the breadth of ready integrations and triggers, mature
business automation, and a template library.

## Dify

Dify is an open-source platform for building AI applications: agents, agentic
workflows and chatbots that draw on your own data (knowledge bases with
retrieval), published as web apps, embeds, REST APIs or MCP servers. Workflows
have nodes such as LLM, knowledge retrieval, HTTP request, tools and Human
Input, which pauses a workflow to ask a person. Plugins add models, tools and
triggers, and a Marketplace shares them. Monitoring covers logs, a dashboard,
annotations and integrations with LangSmith, Langfuse, Opik, W&B Weave, Arize
and Phoenix. It runs on Dify Cloud or as the self-hosted Community Edition with
Docker Compose.

Its license is Apache 2.0 with added conditions: operating a multi-tenant
environment (one tenant is one workspace) needs written permission, and the
logo and copyright in the console and apps must stay.

Where Dify is strong: an all-in-one LLM app platform with RAG, many model
providers, an app front end out of the box and a plugin ecosystem.

## CrewAI

CrewAI is an open-source Python framework (MIT) for multi-agent systems.
**Flows** define the structure: state, event-driven steps, branching and loops;
**Crews** are teams of role-playing agents that collaborate on a task inside a
Flow step. Flow state can be persisted with `@persist`, and `@human_feedback`
(CrewAI 1.8.0 and later) pauses a Flow for a person to approve, reject or
revise. Observability comes through CrewAI tracing on AMP and integrations such
as Langfuse, Arize Phoenix, MLflow, Opik and Datadog.

CrewAI AMP (Agent Management Platform) is the commercial side: deploy crews to
managed infrastructure from GitHub, the CLI or **Crew Studio** (a no-code/low-code
interface), call them through a REST API, stream events by webhook and monitor
traces.

Where CrewAI is strong: role-based multi-agent collaboration with little code,
and a managed path to production.

## PydanticAI

PydanticAI is the Pydantic team's Python agent framework (MIT): typed agents,
structured outputs validated by Pydantic, typed dependency injection and tools,
and many model providers swappable by a string. Around it: Pydantic Graph for
typed graph control flow, Pydantic Evals for grading outputs and tool-call
trajectories, durable execution on engines such as Temporal, DBOS and Prefect
(with human approval of tool calls), step persistence to save, resume and fork
a run, and OpenTelemetry-native instrumentation. Pydantic Logfire is the
company's observability platform (free tier available); any OpenTelemetry
backend works instead.

Where PydanticAI is strong: type safety and testability for developers, wide
model support, and production durability on an engine you already run.

## Using them together

- **Call Superstep from anything.** n8n, Dify (HTTP request node) or a CrewAI or
  PydanticAI program can start a Superstep workflow through the public API or
  the SDKs, for example to put a reviewed, approval-gated step inside a larger
  automation.
- **Call them from Superstep.** HTTP and MCP nodes can reach an n8n webhook, a
  Dify app API or an agent you serve yourself.
- **Move to code.** When a visual workflow outgrows the canvas, export it as a
  LangGraph project and continue in code.

## When to choose another tool

- Choose **n8n** when the job is mostly connecting business apps (CRMs,
  spreadsheets, messaging) with some AI steps, you want a large library of ready
  integrations, and the Sustainable Use License fits your use.
- Choose **Dify** when you want a complete LLM app platform with knowledge
  bases, a ready chat front end, a plugin marketplace and a hosted cloud, and
  its license conditions (no multi-tenant service, keep the branding) fit.
- Choose **CrewAI** when your team writes Python and the problem suits
  autonomous, role-based agents collaborating, optionally with a managed
  platform.
- Choose **PydanticAI** when developers want a typed, code-first agent library
  with strong testing, evals and durable execution, and do not need a visual
  editor.
- Choose **Superstep** when you want LangGraph underneath (with export and a
  LangGraph-compatible API), a visual editor that non-developers can review,
  explicit approvals in Slack, Telegram, WhatsApp, email or Teams, an MIT
  license and self-hosting without a contract, or a Vietnamese UI.

## Sources

- [n8n: Integrate AI](https://docs.n8n.io/advanced-ai/)
- [n8n: Human-in-the-loop for tools](https://docs.n8n.io/build/integrate-ai/ai-examples/human-in-the-loop-for-tools/)
- [n8n: Choose how to use n8n](https://docs.n8n.io/choose-how-to-use-n8n/)
- [n8n license](https://github.com/n8n-io/n8n/blob/master/LICENSE.md)
- [Dify documentation](https://docs.dify.ai/en/introduction)
- [Dify: Human Input node](https://docs.dify.ai/en/self-host/use-dify/nodes/human-input)
- [Dify license](https://github.com/langgenius/dify/blob/main/LICENSE)
- [CrewAI introduction](https://docs.crewai.com/en/introduction)
- [CrewAI: Human feedback in Flows](https://docs.crewai.com/en/learn/human-feedback-in-flows)
- [CrewAI AMP](https://docs-platform.crewai.com/platform/en/introduction)
- [CrewAI license](https://github.com/crewAIInc/crewAI/blob/main/LICENSE)
- [Pydantic AI](https://ai.pydantic.dev/)
- [Pydantic AI license](https://github.com/pydantic/pydantic-ai/blob/main/LICENSE)
