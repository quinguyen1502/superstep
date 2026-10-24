# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0053
- Status: In review (TASK-0090)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Source: owner request in chat, 2026-10-24 (item 1 of 5). Branch `feat/langgraph-project-export` (PR #128) predates the switch to the factory workflow; artifacts added afterwards on the same branch.

## Summary

- Download a workflow as a runnable LangGraph project (Python or TypeScript) that `langgraph dev` serves and LangSmith Studio can open.

## Acceptance Criteria

- `GET /api/workflows/{wid}/export/{python|typescript}/project` returns a reproducible zip: agent file exposing `graph`, `langgraph.json`, dependencies (requirements.txt + pyproject.toml, or package.json + tsconfig.json), `.env.example`, README.
- Code view has a **Project .zip** button with a tooltip (en+vi).
- `langgraph dev` (Python langgraph-cli 0.4.38, JS @langchain/langgraph-cli 1.5.5) serves both exports (`scripts/langgraph_dev_smoke.py`).
- Unit, vitest and e2e (the download is unzipped and checked); handbook en+vi; CHANGELOG.

## Out Of Scope

- A LangSmith Studio check (no account).
- Deploying to LangSmith from Superstep.
