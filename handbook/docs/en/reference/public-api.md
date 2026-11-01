---
hide:
  - navigation
  - toc
---

# Public API reference

The workflow-trigger API (workflow tokens) and public Chat API v1 (anonymous,
studio or app-user identities). The
reference below is rendered from the public OpenAPI spec,
[`openapi.public.json`](openapi.public.json) (the same file as
`docs/api/openapi.public.json` in the repository). A running server also
serves it at `/openapi.public.json`, with an interactive Swagger view at
`/docs/public`.

For a walkthrough with curl, Python and TypeScript examples, see
[Public API and SDKs](../run/public-api.md).
For chat sessions and streaming, see [Chat API](../run/chat-api.md) and
[Third-party auth](../run/chat-third-party-auth.md). Socket frames are specified
by AsyncAPI, linked from the chat guide; they are not HTTP operations below.

<div id="api-reference" class="api-reference" data-spec="../openapi.public.json"></div>
<script src="../javascripts/vendor/redoc.standalone.js"></script>
<script src="../javascripts/api-reference.js"></script>
