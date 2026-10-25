# Superstep vs CrewAI and PydanticAI

This page is for teams that would rather write agents in code than draw them in
a visual studio. CrewAI and PydanticAI are code-first Python agent frameworks,
in the same category as LangGraph itself. Superstep is not a framework: it is a
studio on top of LangGraph. Its workflows compile to a LangGraph `StateGraph`
and export as LangGraph code, so the fair comparison is **Superstep plus
LangGraph** against **CrewAI** or **PydanticAI**. Facts about the other
products come from their own documentation and license files (listed under
[Sources](#sources)) as checked on 25 October 2026; check those pages before
you decide. For visual builders, see
[Superstep vs n8n, Dify, Langflow and Flowise](superstep-vs-visual-builders.md).

## In one sentence each

| Product | What it is |
| --- | --- |
| **Superstep + LangGraph** | Build LangGraph workflows visually in Superstep (MIT), run them as services, and export them as LangGraph Python or LangGraph.js projects when you want to continue in code. |
| **CrewAI** | An open-source Python framework for multi-agent systems (Crews of role-playing agents inside event-driven Flows), with a commercial platform, CrewAI AMP, that adds deployment, tracing and the no-code Crew Studio. |
| **PydanticAI** | A typed Python agent framework from the Pydantic team, with Pydantic Graph, Pydantic Evals, durable execution integrations and the Logfire observability platform around it. |

## Summary comparison

| | Superstep + LangGraph | CrewAI | PydanticAI |
| --- | --- | --- | --- |
| How you build | Draw the graph, or write LangGraph code; export moves from one to the other | Python code (Flows and Crews); no-code Crew Studio in AMP | Python code; YAML/JSON agent specs |
| Core model | Explicit graph: nodes, edges, typed state, checkpoints | Flows (state, events, branching) that call Crews of role-playing agents | A typed agent loop; Pydantic Graph for graph control flow |
| License | MIT (Superstep and LangGraph) | MIT (framework); AMP is commercial | MIT |
| Human in the loop | Human nodes and LangGraph interrupts; approve in the studio, Slack, Telegram, WhatsApp, email or Teams | `@human_feedback` in Flows; resume endpoint in AMP | Human approval of tool calls; long waits through durable engines |
| Durable runs and time travel | Checkpoints in the database, leased worker jobs; fork a finished run from a checkpoint | `@persist` flow state, restore from a saved state | Durable execution on Temporal, DBOS, Prefect and others; step persistence to save, resume and fork |
| Tests, evals, observability | Workflow tests, LangSmith evals, OpenTelemetry traces | AMP tracing; many third-party integrations | Pydantic Evals; OpenTelemetry-native, Logfire |
| Running it as a service | Built in: API tokens, webhooks, schedules, public API with Python and TypeScript SDKs | Your own service, or AMP deployments with a REST API | Your own service; AG-UI and Vercel AI event streams for front ends |

## How Superstep relates to code-first frameworks

- **Same category as LangGraph, not as Superstep.** CrewAI and PydanticAI
  compete with LangGraph as the library your agent is written in. Superstep
  uses LangGraph as its runtime and adds an editor, run history, approvals,
  tests and an API around it.
- **You can leave the canvas.** Any Superstep workflow exports as a runnable
  LangGraph project (see [Export to Python](../guide/python-export.md)), and
  the [LangGraph-compatible API](../run/agent-server-api.md) lets LangGraph
  clients call workflows that stay in Superstep.
- **Code where you need it.** Python and TypeScript Code nodes cover steps
  that are easier to write than to draw.
- **Mixing is fine.** A CrewAI or PydanticAI program can start a Superstep
  workflow through the [public API and SDKs](../run/public-api.md), and a
  Superstep HTTP or MCP node can call an agent you serve yourself.

## CrewAI

CrewAI is an open-source Python framework (MIT) for multi-agent systems.
**Flows** define the structure: state, event-driven steps, branching and loops;
**Crews** are teams of role-playing agents that collaborate on a task inside a
Flow step. Flow state can be persisted with `@persist`, and `@human_feedback`
(CrewAI 1.8.0 and later) pauses a Flow for a person to approve, reject or
revise. Observability comes through CrewAI tracing on AMP and integrations such
as Langfuse, Arize Phoenix, MLflow, Opik and Datadog. The docs include a guide
for moving projects from LangGraph to CrewAI.

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

## When to choose a framework instead

- Choose **CrewAI** when your team writes Python and the problem suits
  autonomous, role-based agents collaborating, optionally with a managed
  platform.
- Choose **PydanticAI** when developers want a typed, code-first agent library
  with strong testing, evals and durable execution, and do not need a visual
  editor.
- Choose **plain LangGraph** when you want LangGraph in code without a studio;
  Superstep exports are a starting point.
- Choose **Superstep** when non-developers should be able to read and change
  the workflow, every branch and approval should be explicit and reviewable,
  you want runs, approvals, tests and an API without building them yourself,
  or you want a Vietnamese UI, while keeping a path to LangGraph code.

## Sources

- [LangGraph license](https://github.com/langchain-ai/langgraph/blob/main/LICENSE)
- [CrewAI introduction](https://docs.crewai.com/en/introduction)
- [CrewAI: Human feedback in Flows](https://docs.crewai.com/en/learn/human-feedback-in-flows)
- [CrewAI AMP](https://docs-platform.crewai.com/platform/en/introduction)
- [CrewAI license](https://github.com/crewAIInc/crewAI/blob/main/LICENSE)
- [Pydantic AI](https://ai.pydantic.dev/)
- [Pydantic AI license](https://github.com/pydantic/pydantic-ai/blob/main/LICENSE)
