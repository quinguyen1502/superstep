# Superstep vs n8n, Dify, Langflow and Flowise

n8n, Dify, Langflow and Flowise are the closest alternatives to Superstep:
like Superstep, they let you build AI workflows on a visual canvas instead of
writing code. They differ in what sits under the canvas, in their licenses and
in how runs pause, resume and get traced. This page compares them fairly so you
can pick the right one. Facts about the other products come from their own
documentation and license files (listed under [Sources](#sources)) as checked
on 25 October 2026; features, plans and licenses can change, so check those
pages before you decide. If you would rather write agents in code, see
[Superstep vs CrewAI and PydanticAI](superstep-vs-agent-frameworks.md); for
LangSmith, see [Superstep vs LangSmith](superstep-vs-langsmith.md).

## In one sentence each

| Product | What it is |
| --- | --- |
| **Superstep** | A visual, self-hosted studio for LangGraph workflows (MIT license), with code export, a LangGraph-compatible API, human-in-the-loop channels and a Vietnamese UI. |
| **n8n** | A workflow automation platform with a visual editor, a large library of app integrations and AI nodes (agents, tools, memory) built on LangChain concepts. |
| **Dify** | An open-source platform for LLM applications: agents, agentic workflows and chatbots on your own data, published as web apps, APIs or MCP servers. |
| **Langflow** | An open-source (MIT) low-code platform for building and deploying AI agents and workflows with a visual builder, an API and an MCP server. |
| **Flowise** | An open-source visual builder for AI agents and LLM flows (Chatflow and Agentflow), self-hosted or on Flowise Cloud. |

## Summary comparison

What runs the workflow, under which license, and where:

| Product | Under the canvas | License | Hosting |
| --- | --- | --- | --- |
| Superstep | Compiles to a LangGraph `StateGraph` | MIT | Self-hosted (Docker, PaaS); free |
| n8n | n8n's own engine; AI nodes implement LangChain concepts | Sustainable Use License (source-available; internal and non-commercial use limits); `.ee` files need an Enterprise license | n8n Cloud or self-hosted Community edition; paid enterprise plans |
| Dify | Dify's own workflow engine | Apache 2.0 with conditions (no multi-tenant service without permission; keep logo and copyright) | Dify Cloud or self-hosted Community Edition (Docker Compose) |
| Langflow | Langflow components; LangChain components are an opt-in bundle | MIT | Self-hosted (Docker, Kubernetes, cloud platforms) or Langflow Desktop |
| Flowise | Agentflow V2: native Flowise nodes; the older Agentflow V1 Multi-Agents and Sequential Agents are built on LangGraph | Apache 2.0, except the enterprise directory and files with their own notice | Flowise Cloud or self-hosted (npm, Docker, cloud guides) |

How runs pause, resume and get checked:

| Product | Human in the loop | Durable runs | Tests, evals, observability |
| --- | --- | --- | --- |
| Superstep | Human nodes, and approval before an Agent node's tool calls; approve in the studio, Slack, Telegram, WhatsApp, email or Teams, with deadlines | Checkpoints in its database (SQLite or Postgres): paused and running queue runs continue after a restart or a worker crash; time travel: fork a finished run from a checkpoint | Workflow tests, LangSmith evals, OpenTelemetry traces |
| n8n | Human review of AI Agent tool calls; Slack "send and wait" approvals | Queue mode with workers | Evaluations (test cases, metrics); OpenTelemetry for self-hosted |
| Dify | Human Input node | Not covered by the sources | Logs, dashboard, annotations; LangSmith, Langfuse, Opik, Phoenix and others |
| Langflow | Human Input component; approval of agent tool calls | HITL pauses at a checkpoint and resumes from it; otherwise not covered by the sources | Playground; LangSmith, Langfuse, Opik, Arize integrations |
| Flowise | Human Input node; "Require Human Input" on agent tools | Agentflow V2 saves checkpoints so a paused run resumes after a restart | Evaluations; Langfuse, LangWatch, Lunary, Opik, Arize, Phoenix |

How you call it and take it elsewhere:

| Product | API, SDK, MCP | Code export |
| --- | --- | --- |
| Superstep | Public run API, Python `superstep` and TypeScript `@superstep/sdk` SDKs, Agent Server API subset at `/api/lg`, workflows as MCP tools at `/mcp` | Runnable LangGraph Python or LangGraph.js project |
| n8n | REST API and webhooks | No (workflows export as JSON) |
| Dify | REST API, `difyctl` CLI, publish apps as MCP servers | No |
| Langflow | Run API, webhooks, MCP server and client, Flow DevOps Toolkit SDK | No (flows export as JSON) |
| Flowise | REST API (Prediction and others) | Not covered by the sources |

## Superstep

- **Visual LangGraph.** Graphs are drawn on a canvas (14 node types, a typed
  state with reducers, loops, parallel branches, subgraphs, Human nodes) and
  compile to a LangGraph `StateGraph`. Python and TypeScript Code nodes run in
  a locked Docker sandbox (on the host on managed platforms) when you need
  code. See [Nodes](../guide/nodes.md).
- **An Agent node inside the graph.** A model picks and calls the tools you
  list (MCP server tools, HTTP requests, built-in functions, knowledge base
  search) for up to a set number of rounds; any tool can need an approval
  before each call. Each model and tool call is a checkpointed step, so it
  shows in the trace and is not repeated after a restart (see
  [Agent node](../guide/agent.md)). An Agent can call another workflow as a
  tool, so a supervisor agent hands work to specialist agents, and the
  specialist's steps show under the call.
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
  jobs, effectively-once side effects, step-by-step runs and time travel:
  inspect a finished run's checkpoints, edit a state and fork a new run.
- **Tests and traces.** Workflow tests with checks (see
  [Workflow tests](../run/tests.md)), optional LangSmith datasets and
  experiments, OpenTelemetry traces (see [Traces](../run/traces.md)).
- **Services, not only a studio.** API tokens, signed webhooks, cron schedules,
  chat triggers, a public chat page with an embeddable chat bubble (see
  [Chat](../run/chat.md#publish-a-chat)), and a public API with Python and
  TypeScript SDKs (see [Public API and SDKs](../run/public-api.md)).
- **Self-hosted, MIT.** SQLite by default or Postgres with pgvector, optional
  Redis and worker, Docker images on GHCR and one-click PaaS deploys (see
  [Deploy](../operate/deploy.md)). Vietnamese and English UI and handbook.

What Superstep does not try to be: it has far fewer ready integrations than the
other four (it connects through HTTP, MCP servers, email and its chat
channels), no hosted cloud service and no marketplace. Several agents work
together only as a supervisor calling other workflows as tools: there are no
hand-offs between agents and no agents that talk freely to each other.

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

## Langflow

Langflow is an MIT-licensed, Python-based low-code platform for building and
deploying agents and workflows with a visual builder. Flows are made of
components; an Agent component can use any component as a tool, including
other agents and MCP servers, and LangChain components are available as an
opt-in bundle. Flows run through the Langflow API or webhooks, can be served
through a Langflow MCP server, and are tested in the Playground. Human-in-the-Loop
"pauses a flow, creates a checkpoint, and waits for a human decision", either
at a Human Input component or when an agent tries to call a tool that needs
approval. Traces can go to LangSmith, Langfuse, Opik or Arize. Flows export as
JSON, and the Flow DevOps Toolkit SDK versions, tests and deploys them from the
terminal. It runs locally, as Langflow Desktop, or deployed with Docker,
Kubernetes or a cloud platform.

Where Langflow is strong: a large component library, an MIT license, MCP in
both directions, and Python custom components.

## Flowise

Flowise is a visual builder for AI agents and LLM flows. Chatflows build
chatbots and RAG flows from LangChain-based nodes; Agentflow V2 builds
multi-step and multi-agent workflows from native Flowise nodes with a shared
flow state. The docs say Agentflow V1 (being deprecated) relied on external
frameworks, and its Multi-Agents and Sequential Agents are built on LangGraph;
V2 no longer is. In Agentflow V2, human-in-the-loop (a Human Input node, or
"Require Human Input" on an agent's tools) pauses execution, and "each
checkpoint is saved, allowing the workflow to resume from the same point even
after an application restart". Flowise has Evaluations, analytics integrations
(Langfuse, LangWatch, Lunary, Opik, Arize, Phoenix) and a REST API. It runs on
Flowise Cloud or self-hosted with npm, Docker or one of many cloud guides.

Its license is Apache 2.0, except the `packages/server/src/enterprise`
directory and files with their own copyright notice.

Where Flowise is strong: quick chatbot and RAG building, an approachable
agent canvas with checkpointed human input, and many deployment guides.

## Using them together

- **Call Superstep from them.** n8n, Dify, Langflow or Flowise can start a
  Superstep workflow over HTTP through the public API, for example to put a
  reviewed, approval-gated step inside a larger automation.
- **Call them from Superstep.** HTTP and MCP nodes, or an Agent node's HTTP and
  MCP tools, can reach an n8n webhook, a Dify app API, a Langflow MCP server or
  a Flowise prediction endpoint.

## When to choose another tool

- Choose **n8n** when the job is mostly connecting business apps (CRMs,
  spreadsheets, messaging) with some AI steps, you want a large library of
  ready integrations, and the Sustainable Use License fits your use.
- Choose **Dify** when you want a complete LLM app platform with knowledge
  bases, a ready chat front end, a plugin marketplace and a hosted cloud, and
  its license conditions (no multi-tenant service, keep the branding) fit.
- Choose **Langflow** when you want an MIT-licensed visual builder with a
  large component library, Python custom components and MCP serving.
- Choose **Flowise** when you want to stand up chatbots, RAG and agent flows
  quickly, self-hosted or on Flowise Cloud.
- Choose **Superstep** when you want LangGraph underneath (with code export
  and a LangGraph-compatible API), explicit approvals in Slack, Telegram,
  WhatsApp, email or Teams, time travel over checkpoints, an MIT license and
  self-hosting without a contract, or a Vietnamese UI.

## Sources

- [n8n: Integrate AI](https://docs.n8n.io/advanced-ai/)
- [n8n: Human-in-the-loop for tools](https://docs.n8n.io/build/integrate-ai/ai-examples/human-in-the-loop-for-tools/)
- [n8n: Choose how to use n8n](https://docs.n8n.io/choose-how-to-use-n8n/)
- [n8n license](https://github.com/n8n-io/n8n/blob/master/LICENSE.md)
- [Dify documentation](https://docs.dify.ai/en/introduction)
- [Dify: Human Input node](https://docs.dify.ai/en/self-host/use-dify/nodes/human-input)
- [Dify license](https://github.com/langgenius/dify/blob/main/LICENSE)
- [Langflow documentation index](https://docs.langflow.org/llms.txt)
- [Langflow: Human-in-the-Loop](https://docs.langflow.org/human-in-the-loop)
- [Langflow: LangChain bundle](https://docs.langflow.org/bundles-langchain)
- [Langflow: Import and export flows](https://docs.langflow.org/concepts-flows-import)
- [Langflow license](https://github.com/langflow-ai/langflow/blob/main/LICENSE)
- [Flowise: Agentflow V2](https://docs.flowiseai.com/using-flowise/agentflowv2)
- [Flowise: Sequential Agents (V1)](https://docs.flowiseai.com/using-flowise/agentflowv1/sequential-agents)
- [Flowise: Human in the loop](https://docs.flowiseai.com/tutorials/human-in-the-loop)
- [Flowise license](https://github.com/FlowiseAI/Flowise/blob/main/LICENSE.md)
