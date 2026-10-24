# Requirement

## Metadata

- Project: superstep
- Requirement ID: REQ-0052
- Status: In review (TASK-0089)
- Owner: Thái Quí Nguyễn
- Created: 2026-10-24
- Updated: 2026-10-24
- Source: owner request in chat, 2026-10-24 (item 5 of 5: comparison page, fair tone, official sources re-verified).

## Summary

- A handbook page (en+vi) comparing Superstep with LangSmith Studio and LangSmith Agent Builder, citing LangChain's official pages, and listing the interop features from TASK-0087/0088 and #128/#129.

## Acceptance Criteria

- Page `reference/superstep-vs-langsmith.md` in en and vi, in both navs and the reference index; no emoji.
- Cites https://docs.langchain.com/langsmith/studio, https://www.langchain.com/pricing, https://docs.langchain.com/langsmith/deploy-to-self-hosted-overview, https://www.langchain.com/blog/langsmith-agent-builder-generally-available, re-checked on 2026-10-24.
- States Developer $0 / Plus $39 per seat and that self-hosting is Enterprise only; positions Superstep, Studio and Agent Builder fairly; mentions project export, the /api/lg API, LangSmith evals and time travel.
- Strict handbook builds pass; CHANGELOG Unreleased.

## Out Of Scope

- Feature claims beyond the four sources.
