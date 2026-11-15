# Requirement

## Metadata

- Project: langgraph-studio
- Requirement ID: REQ-0036
- Status: Implemented
- Owner: Thái Quí Nguyễn
- Created: 2026-10-19
- Updated: 2026-10-19
- Source: owner question "does langgraph support a Jev Model?", the reference https://typesafe.ai/blog/introducing-system-one-models-and-jev, and the reply "Start right away" (2026-10-19)

## Summary

A Decision node asks TypeSafe's Jev typed questions (choice, score, noul) about the state and writes the answers to state fields.

## Problem Or Opportunity

- Jev is a "System One" model. It returns typed decisions with calibrated probabilities instead of text, so the LLM node cannot use it.
- Routing on an LLM's free text needs fuzzy label matching. A typed choice routes exactly.

## Scope

### In Scope

- A TypeSafe credential (provider registry, kind `decision`), the `decision` node (validation, run, usage and cost, ledger reuse), the editor's question builder, docs, tests

### Out Of Scope

- `box` questions and image assets
- Request compression (SDKs use zstd for bodies over 1 KiB; plain JSON is accepted)
- Confidence-based routing helpers (a Condition on a number field can follow later)

## Stakeholders Or Users

- Workflow authors who classify, score, or route

## Desired Behavior

- See DEC-0039.

## Business Rules

- 1–20 questions per node. Ids are unique identifiers. `choice` has 2–255 unique labels. `score` has 2–10 non-empty levels. `noul` takes no criteria.
- A question's field must exist and fit the answer: text for a choice, a number for a score or a noul. It uses the `replace` reducer. `output_field` must be an object field. At least one of them is set.
- Only a TypeSafe credential can serve a Decision node. TypeSafe credentials are not offered to LLM nodes.

## Constraints

- No new dependency (no `typesafe-sdk`). One HTTP call through the provider layer, which handles error mapping. No new API error codes.

## Acceptance Criteria

- Offline (no credential, no `TYPESAFE_API_KEY`): the choice picks the option named in the text, and a Condition routes on it. Usage is recorded as mock with cost 0.
- With a credential: `POST /v1/systemone` with a Bearer key. The body has typed `state`, choice criteria as an object, and score criteria as a list. The answers go to their fields and `output_field`. Usage is priced for `jev`. The key never appears in events.
- A wrong key gives `PROVIDER_AUTH_FAILED`. A chat credential on a Decision node gives a readable node error.
- **Test connection** for TypeSafe returns `jev-latest` and the served model version. `/api/providers` reports `kind`.
- A recovered run reuses the stored answers instead of calling again.
- The editor builds questions (add, change type, options, levels, field). The saved node matches.

## Edge Cases

- A `noul` question needs no options. Changing a question's type resets its options or levels and its field.

## Assumptions

- The API shape is taken from docs.typesafe.ai on 2026-10-19 (Quick Start, API reference, Score). Jev is in early access, so the live API could not be called from here.

## Open Questions

- None

## Related Artifacts

- Decision: `.factory-state/decisions/DEC-0039-jev-decision-node.md`
- Task: `.factory-state/tasks/done/TASK-0050-jev-decision-node.md`
