# Design Artifact

## Metadata

- Project: superstep
- Design ID: DES-0001
- Status: Implementation proposal within owner-authorised REQ-0083; review on task PRs
- Owner: Thái Quí Nguyễn
- Created: 2026-11-01
- Updated: 2026-11-01
- Related Requirements: REQ-0083
- Related Architecture: DEC-0081

## Context

Reuse the editor's Settings/Data/Execution tabs, Chat triggers dialog and Settings MCP connection/tool surfaces. No vendor-specific canvas types.

## Users And Goals

- Builder: configure an inbound event and map data to state, select a managed tool and map typed arguments, choose one fallback model without copying a graph branch.
- Operator: manage encrypted secrets and scoped event admission; distinguish failure from an uncertain external write.

## User Flows

- Model policy: select LLM node -> choose primary credential/model -> enable fallback -> select a different credential/model -> save -> run; trace shows the selected model and failover. Disabled policy removes its stored configuration.
- Events: workflow trigger settings -> choose source/place and admission -> map text and metadata to declared fields -> save -> test event -> run appears in existing History.
- Tools: Settings connection registry -> add managed connection -> discover tools -> existing MCP node or Agent selects connection/tool -> fill schema-derived arguments -> run -> show result/outcome in existing trace.

## Information Architecture

The canvas continues to express computation/control flow. Connections live in Settings; event bindings live with workflow triggers; model fallback lives with model settings. Telegram/Google appear as connection/tool choices, not graph types.

## Surface Or Screen States

- Empty: explain what to configure and link to the existing credential/connection surface.
- Editing: labelled controls, visible current selections and bounded input.
- Invalid: field-specific translated errors; save cannot persist an incomplete policy or invalid mapping.
- Failure: use existing errorText/eventErrors. Unknown external outcome explicitly asks for reconciliation, never offers an unsafe automatic repeat.

## Interaction Behavior

Selects, inputs, switches, dialogs and alerts use shadcn/ui and theme tokens. Destructive connection/trigger actions use ConfirmDeleteDialog and exact typed name. Feature defaults are off; old workflows preserve their behavior.

## Content And Messaging

Every new UI string in en/vi with identical keys. Explain that fallback is a second model attempt, and event sender metadata is not a studio account. Provider/model technical ids remain visible where needed to identify configuration.

## Accessibility

Associate every label/control, name icon buttons, retain keyboard/focus behavior of shared dialogs/selects and expose validation without colour alone.

## Responsive Or Adaptive Behavior

Editor controls remain single-column within its config panel. Dialog layouts wrap at narrow widths and keep actions reachable without horizontal overflow.

## UX Acceptance Criteria

- Policies and bindings survive save/reopen; disabling removes settings; deleting requires typed-name confirmation.
- No new canvas type for a vendor; existing MCP argument mapping works for managed tools.
- Screenshots and browser tests cover changed forms in en/vi and light/dark as applicable.

## Risks

Do not overwhelm the first form with future OAuth/plugin configuration; expose only supported adapter settings.

## Assumptions

- Reuse existing design primitives; no separate visual branding or design system change.

## Open Questions

- None blocking initial implementation; detailed fields recorded on each task as implemented.

## Impacted Artifacts

- REQ-0083, PLAN-0003, DEC-0081 and the feature task review/QA records.
