---
hide:
  - navigation
  - toc
---

# Public API reference

The workflow-trigger API uses workflow tokens. Public Chat API v1 supports
anonymous, Studio or app-user identities. Dataset Connected v1 uses Dataset API
tokens. The reference below is rendered from the public OpenAPI spec,
[`openapi.public.json`](openapi.public.json) (the same file as
`docs/api/openapi.public.json` in the repository). A running server also
serves it at `/openapi.public.json`, with an interactive Swagger view at
`/docs/public`.

For a walkthrough with curl, Python and TypeScript examples, see
[Public API and SDKs](../run/public-api.md).
For chat sessions and streaming, see [Chat API](../run/chat-api.md) and
[Third-party auth](../run/chat-third-party-auth.md). Socket frames are specified
by AsyncAPI, linked from the chat guide; they are not HTTP operations below.

For Dataset rows, create a token under **Datasets → Access → Dataset API tokens**
and send it as `Authorization: Bearer dsat_…`. The Dataset operation below covers
Find, Aggregate, Get, Insert, Upsert and Delete, with a request example for
each. Use the token for its own Dataset and reuse the same `operation_id` and
body when retrying a write or delete.

<div id="api-reference" class="api-reference" data-spec="../openapi.public.json"></div>
<script src="../javascripts/vendor/redoc.standalone.js"></script>
<script src="../javascripts/api-reference.js"></script>
