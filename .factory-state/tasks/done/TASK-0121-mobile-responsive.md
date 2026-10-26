# Task

## Metadata

- Project: superstep
- Task ID: TASK-0121
- Status: done
- 2026-10-26: PR #150 merged into develop (c4959a7) with the owner's approval; moved to done. The owner asked to
  merge without a separate review or QA artifact.
- Owner: Thái Quí Nguyễn
- Created: 2026-10-26
- Updated: 2026-10-26
- Requirement IDs: none (owner request in chat, 2026-10-26)
- Design IDs: none (layout below; `docs/ui-conventions.md` rules apply)
- Architecture IDs: none

## Objective

Make the studio usable on a phone, and split the node Config panel into one fixed set of tabs shared by every node.

## Scope

### In Scope

- Below 768px (Tailwind `md`, `useIsMobile` in `lib/use-viewport-width.ts`):
  - Workflow list: no sideways scroll; the toolbar wraps, search takes the full width, the Nodes and Updated columns
    hide, the last-run time hides below 640px.
  - Settings: smaller gutters; the section links scroll sideways in one row.
  - Editor (`EditorLayout` `mobile`): one pane at a time (Canvas, Nodes, Config, Run, and Chat while it is open),
    switched by a shadcn Tabs bar at the bottom. Panes stay mounted, only hidden. A dot on Config while a node or edge
    is selected. Run switches to the Run pane; opening the chat shows the Chat pane, closing it returns to the canvas.
  - Editor header: back, name, Save, Run, Chat and ⋯ as icon buttons; Step, Run to, undo/redo, the info badges and the
    account controls hide (they stay on the workflow list).
  - Palette: a tap on a card adds the node in the middle of the canvas (touch screens cannot drag), with a hint.
  - Canvas: no minimap, zoom out to 0.2 so a whole workflow fits.
  - Run panel: input above the logs; the run picker shrinks, "View all" is icon-only.
- en + vi strings (`editor.mobileNav.*`), e2e `frontend/e2e/mobile.spec.ts`.
- Node Config tabs (owner, 2026-10-26: one set of tabs for all nodes, so builders learn where a setting lives,
  rather than tabs that change per node):
  - Node icon, id and Label above a tab bar **Settings · Data · Execution** (vi: Cài đặt · Dữ liệu · Thực thi), the same
    three, same order, for every node.
  - Settings = what the node does; Data = every picker of a state field (output, steps, history, loop fields, the
    Condition field, Decision answer fields, input fields); Execution = retry, wait, timeout, cache, and limits
    (Agent max rounds, For each max items).
  - A tab a node does not use is disabled in place; Start and End show all three disabled with a note.
  - The chosen tab is kept while selecting other nodes (falls back to Settings where it is disabled).
  - A dot on a tab that needs attention: Data when a required output field is empty, Settings for an Agent without
    tools.
  - `AgentSettings` exports `AgentData` / `AgentExecution`; `EmailData`, `DecisionData` hold their field pickers;
    `NodeRuntime` drops its own heading (the tab names it).
  - Rule 12 in `docs/ui-conventions.md`; handbook `guide/nodes.md` (Config tabs), `guide/agent.md`,
    `start/quickstart.md` (en + vi); e2e `frontend/e2e/config-tabs.spec.ts`; `decision`, `foreach`, `quickstart`
    specs open the tab first.

### Out Of Scope

- Regenerating the quickstart images and promo frames (`quickstart.spec.ts` capture run); the LLM and Human
  config shots still show one scrolling panel until they are captured again.
- Tablet-specific layouts (768px and up keep the desktop panels as before).
- In scope by owner request: `templates.spec.ts` expects 13 built-in templates (stale since TASK-0119).

## Related Artifacts

- Decisions: DEC-0008 (`docs/ui-conventions.md`), DEC-0055 (alignment and sizing)
- Previous layout work: TASK-0038 (resizable panels), TASK-0085 (chat side panel)

## Constraints

- shadcn/ui components and theme tokens only; no hand-set control sizes (`npm run lint:ui`).
- Desktop layout unchanged.

## Acceptance Criteria

- [x] At 375×812 the workflow list, Settings and the editor never scroll sideways.
- [x] The editor shows one pane at a time with the bottom tab bar; Save, Run, Chat and ⋯ stay reachable.
- [x] A tap on a palette card adds that node, selected, and shows the canvas.
- [x] Selecting a node marks Config; Config shows the node at full width.
- [x] Run shows the Run pane with the input above the logs; Chat opens and closes as a pane.
- [x] From 768px the editor keeps the side-by-side panels.
- [x] Light and dark themes checked.
- [x] Every node's Config shows Settings · Data · Execution in that order; unused tabs are disabled, not hidden.
- [x] The chosen tab is kept across nodes; a dot marks a missing required output field and an Agent without tools.
- [x] Viewers can switch tabs: the tab bar sits outside the disabled fieldset (checked in the DOM; no viewer e2e).

## Validation

- `npx tsc -b`: pass.
- `npm run lint`: `lint:ui` no hits; no new oxlint warnings.
- `npx vitest run`: 105 passed.
- `npx playwright test e2e/mobile.spec.ts e2e/panel-layout.spec.ts e2e/layout.spec.ts e2e/resize.spec.ts
  e2e/alignment.spec.ts e2e/studio.spec.ts e2e/palette.spec.ts e2e/agent-node.spec.ts`: 30 passed (mobile part).
- Full e2e after the Config tabs (`E2E_CODE_RUNTIME=subprocess`, capture specs excluded): 95 passed, 3 skipped,
  1 failed: `templates.spec.ts:19` expected 12 built-in templates, but `engine/templates.py` has 13 since TASK-0119
  added the Support agent template (it failed on `develop` too). Fixed here at the owner's request (2026-10-26): the
  spec expects 13 and checks `builtin-support-agent`; `templates.spec.ts` 3 passed.
- `quickstart.spec.ts` (capture run) not run: it rewrites the promo frames.

## Research: node Config as tabs

Measured in the studio (Agent node, Config panel content height):

| Agent node | Content height | Phone (700px visible) | Desktop (≈540px visible at 900px tall) |
|---|---|---|---|
| no tools | 1583px | 2.3 screens | 2.9 screens |
| 1 HTTP tool | 2128px | 3.0 screens | 3.9 screens |
| HTTP + built-in tool, approval on | 2796px | 4.0 screens | 5.2 screens |

The tool list starts 923px down and the approval settings 1867px down, so neither is on screen when the node opens.
Short nodes (Condition, Join, Subgraph, Retriever, End) fit in one screen.

Recommendation (first draft, replaced by the owner's direction above): tabs for long nodes only.

- Keep the header (icon, type, id) and Label above the tabs, always visible.
- Tabs (shadcn `Tabs`, `TabsList size="sm"`, at most four so they fit the 260px minimum panel width):
  - **General**: the node's own settings (model, prompts, fields).
  - **Tools (N)**: Agent only, with the count.
  - **Approval**: Human, and Agent once a tool needs approval (approvers, channels, deadline).
  - **Advanced**: input fields + retry/timeout/cache (`NodeInput`, `NodeRuntime`), shared by every runtime node.
- Nodes with only General keep today's single scroll (no tab bar with one tab).
- A tab with a problem shows it (dot or count), e.g. "no tools yet" or a duplicate tool name, because a hidden error is
  easy to miss.
- Remember the last tab per node type while switching nodes.
- Costs: e2e specs that fill Agent, Human and runtime fields must open the tab first; browser find no longer finds
  text in hidden tabs.
- Accordion was considered: it keeps one flow but stays long when sections are open, and the Agent sections are
  independent of each other, which suits tabs.

After the change (Agent with one built-in tool, phone): Settings 744px, Data 429px, Execution 399px, against 2128px
in one scroll before.
