# Browser first-delivery examples

Studio-only fixtures for REQ-0086. Executable exports wait for TASK-0251/0252.

## `lookup_shipment.json`

Typed browser **recipe** workflow: authorised URL + order ID → reviewed fill/click
→ bounded shipment extraction. Import in Studio, point every MCP action at your
saved browser connection (Settings → MCP), adapt literal role/text selectors to
the reviewed page layout, then enable the recipe on Start.

English setup guide: handbook **Guide → Browser tools**.
