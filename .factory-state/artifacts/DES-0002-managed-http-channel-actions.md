# Design

- Design ID: DES-0002
- Project: superstep
- Status: implementation direction within owner-authorised REQ-0084
- Created/Updated: 2026-11-02
- Related: REQ-0084, DEC-0082, PLAN-0004

Reuse Settings → MCP → Managed and existing node/Agent tool pickers. HTTP settings show base URL and a multiline JSON tool-definition field with an initial reviewed example, plus a write-only encrypted header JSON field. Plain strings/numeric fields and existing channel resource selectors remain schema-driven. Select a channel-service adapter, select an existing matching channel, configure its fixed target where applicable, discover tools and map arguments in existing controls.

Use shadcn Input/Textarea/Select and theme tokens, en/vi labels, associated labels/control IDs and visible JSON setup help. The form wraps at narrow widths. Preserve typed-name deletion for connections. Operation panels distinguish confirmed submission from unknown; no button offers an automatic resend. No new canvas type or separate integration settings page.

Acceptance: create/edit/discover/use/reopen works; secrets stay write-only; input schema drives existing node/Agent arguments. Invalid definitions produce existing translated errors. Browser screenshots include en/vi and light/dark forms and operation state. A fixed target cannot be supplied by the model. Documentation gives complete synthetic JSON examples and explains response schemas and service-specific delivery limitations.
