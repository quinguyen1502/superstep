# Superstep vs LangSmith

Superstep and LangSmith both work with LangGraph agents, but they solve
different problems and work well together. This page compares them on what
each one is built for, so you can pick the right tool or combine them. Facts
about LangSmith come from LangChain's own pages (listed under
[Sources](#sources)) as checked on 24 October 2026; prices and plans can
change, so check those pages before you decide.

## In one sentence each

| Product | What it is |
| --- | --- |
| **Superstep** | A visual, self-hosted builder for LangGraph-style workflows (MIT license), with code export, human-in-the-loop channels and a Vietnamese UI. |
| **LangSmith Studio** | A code-first agent IDE from LangChain: visualize, run and debug graphs that implement the Agent Server API, with deep tracing, evaluation and managed deployment around it. |
| **LangSmith Agent Builder** | LangChain's no-code way to build agents: describe a goal in plain language and it plans the instructions, tools and subagents. |

## Superstep

- **Visual first.** Graphs are drawn on a canvas: nodes, edges, a typed state
  schema, loops, parallel branches and subgraphs. Editors do not need to write
  code; Code nodes are there when they want to.
- **Self-hosted and open source.** MIT license. Runs with Docker Compose or on a
  PaaS on your own infrastructure; your data stays there.
- **Code export.** Any workflow exports to a LangGraph Python or LangGraph.js
  file (see [Export to Python](../guide/python-export.md)).
- **Human in the loop where people already are.** Human nodes pause a run and
  ask for an answer in Slack, WhatsApp, the approvals inbox or a web chat (see
  [Human approval](../run/human-approval.md) and [Chat](../run/chat.md)).
- **Vietnamese and English UI and handbook.**
- **Built-in run tools.** Step-by-step runs, run history, workflow tests with
  checks (see [Workflow tests](../run/tests.md)) and OpenTelemetry traces.

## LangSmith Studio

According to the Studio documentation, Studio is "a specialized agent IDE" for
agents that implement the Agent Server API protocol, integrated with tracing,
evaluation and prompt engineering. Its listed features include visualizing the
graph, running and interacting with the agent, managing assistants and
threads, iterating on prompts, running experiments over a dataset, managing
long-term memory, debugging state with time travel and one-click deploy to
LangSmith Cloud. It works with graphs deployed on LangSmith or running locally
through the Agent Server (for example `langgraph dev`), and has a graph mode
and a chat mode.

Where LangSmith is strong:

- **Tracing and evaluation depth.** LangSmith is LangChain's observability and
  evaluation platform; datasets, experiments, feedback and prompt iteration
  are first-class.
- **Managed deployment.** The Plus plan includes LangSmith Deployment (one free
  small serverless deployment), with more capacity charged on usage.
- **Code-first control.** Your graph is your own Python or JavaScript code.

## LangSmith Agent Builder

LangChain announced Agent Builder as generally available on 13 January 2026.
It is a no-code product: you describe the goal in your own words, and it
writes the instructions, picks tools and adds subagents when needed. Agents
learn from feedback through memory, can ask permission before sensitive
actions, can be shared and cloned in a workspace, connect tools through a
remote MCP server and can be called through an API. The announcement says it
is available on all LangSmith plans. On the current pricing page, the no-code
product for building agents "using everyday language, not code" is listed as
**LangSmith Fleet**.

Agent Builder and Superstep are both ways to build agents without writing
code, with different approaches: Agent Builder lets the agent plan its own
steps from a goal; Superstep has you draw the steps, so every path, branch and
approval is explicit and reviewable. Where the model should choose, a
Superstep [Agent node](../guide/agent.md) picks and calls the tools you list
inside one drawn step, and asks for approval before the tools you mark.

## Pricing and hosting

| | Superstep | LangSmith (Studio, Deployment, Agent Builder) |
| --- | --- | --- |
| License | MIT, open source | Commercial service |
| Price | Free; you pay for your own servers and model API usage | Developer $0 (1 seat, 5k base traces per month included), Plus $39 per seat per month (10k base traces per month included), Enterprise custom; usage beyond the allowances is pay as you go |
| Self-hosting | Yes, always | Enterprise plan only (self-hosted and hybrid options); Developer and Plus are cloud only |
| Data location | Your infrastructure | LangChain's cloud (US or EU), or your VPC with Enterprise self-hosted |

The self-hosted LangSmith overview states that "Self-hosted deployments
require an Enterprise plan and the LangSmith license key delivered with that
plan", and offers three topologies: full platform, hybrid and a standalone
Agent Server.

## Using them together

Superstep speaks LangGraph, so you do not have to choose one side:

| Feature | What it gives you |
| --- | --- |
| **Runnable LangGraph project export** | Download a workflow as a project with `langgraph.json`, dependencies and `.env.example`; `langgraph dev` serves it, so you can open it in LangSmith Studio or deploy it to LangSmith. |
| **LangGraph-compatible API** | A subset of the Agent Server API (assistants, threads, runs, streaming, interrupts) at `/api/lg`, so the official `langgraph-sdk` clients and `RemoteGraph` can run Superstep workflows. |
| **LangSmith evals and trace links** | With a LangSmith API key, workflow test runs go to LangSmith as a dataset and an experiment, and runs traced to LangSmith link to their trace. |
| **Time travel** | Inspect a run's checkpoints in the Run panel, edit a state and fork a new run from it, as Studio does for code-first graphs. |

A common setup: business users and reviewers build and approve workflows in
Superstep, developers export them as LangGraph projects when they need custom
code, and the team uses LangSmith for tracing and evaluation across both.

## Which one to pick

- Choose **Superstep** when you need self-hosting without an Enterprise
  contract, a visual editor for non-developers, approvals in Slack, WhatsApp or
  a web chat, a Vietnamese UI, or an open-source license.
- Choose **LangSmith Studio** when your agents are written in code and you
  want LangChain's tracing, evaluation and managed deployment in one place.
- Choose **LangSmith Agent Builder** when you want agents that plan their own
  steps from a plain-language goal, hosted by LangChain.

## Sources

- [LangSmith Studio](https://docs.langchain.com/langsmith/studio)
- [LangSmith pricing](https://www.langchain.com/pricing)
- [Deploy to self-hosted](https://docs.langchain.com/langsmith/deploy-to-self-hosted-overview)
- [Now GA: LangSmith Agent Builder](https://www.langchain.com/blog/langsmith-agent-builder-generally-available)
