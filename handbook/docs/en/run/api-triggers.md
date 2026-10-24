# API triggers and webhooks

Any workflow can be started over HTTP by another service. To start one from a
Slack or Telegram message instead, see [Chat triggers](chat-triggers.md).
For the Python and TypeScript SDKs and every error code, see
[Public API and SDKs](public-api.md).

![Trigger via API](../images/api-trigger.png)

## Before you begin

- Owner access to the workflow: you own it, or you are an admin. Editors of a
  shared workflow can run it but cannot create tokens.
- A saved workflow. API runs use the latest saved version.
- The worker running (by default it runs inside the API process).

## Create a token

**⋯ → API** in the editor creates a workflow token (`wft_…`) and a signing
secret (`whsec_…`). Each is shown once. Revoke either at any time; rotating
the secret keeps the previous one valid for `STUDIO_SECRET_GRACE` seconds
(default one day).

## Start a run

```bash
curl -X POST http://localhost:8080/api/hooks/workflows/<wid>/runs \
  -H "Authorization: Bearer wft_..." -H "Content-Type: application/json" \
  -d '{"input": {"message": "hi"}, "mode": "sync"}'
```

| Field | Meaning |
| --- | --- |
| `input` | The initial state. |
| `mode` | `async` (default) returns `202 {run_id, status: "queued"}` at once. `sync` waits for `final_state`, at most `STUDIO_SYNC_WAIT_MAX` seconds (default 30), then falls back to `202` with `poll_url`. |
| `callback_url` | Optional. Receives a POST with `X-Studio-Event: run.finished` when the run ends. |

Poll with `GET /api/hooks/workflows/<wid>/runs/<run_id>`. A bad token is
`401 TRIGGER_TOKEN_INVALID`. API runs carry an **API** badge in History.

## Verify callbacks

Each callback carries `X-Studio-Signature: t=<timestamp>,v1=<hex>`, where `v1`
is HMAC-SHA256 of `"<t>.<raw body>"` with the signing secret. Reject a
timestamp more than five minutes off. During a secret rotation the header
carries two `v1` values; accept the request when any of them matches.

```python
import hashlib, hmac, time

def verify(secret: str, header: str, body: bytes, tolerance=300) -> bool:
    parts = dict(p.split("=", 1) for p in header.split(","))
    if abs(time.time() - int(parts["t"])) > tolerance:
        return False
    mac = hmac.new(secret.encode(), f'{parts["t"]}.'.encode() + body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(mac, parts["v1"])
```

## Deliveries and retries

Deliveries are stored with status, attempts, HTTP code and latency under
**Deliveries** in the API dialog, with **Resend**. Network errors and non-2xx
responses retry with backoff
`min(STUDIO_WEBHOOK_BACKOFF_BASE^n, STUDIO_WEBHOOK_BACKOFF_MAX)`, up to
`STUDIO_WEBHOOK_MAX_ATTEMPTS`. Receivers should deduplicate on `run_id` plus
the event.

Callback URLs go through the SSRF guard: the hostname is resolved once, every
address is checked, and the connection goes to that IP without following
redirects. Private addresses fail at once unless
`STUDIO_ALLOW_PRIVATE_CALLBACKS=1`.

## Rate limits

Each token may start `STUDIO_TRIGGER_RATE_LIMIT` runs per
`STUDIO_TRIGGER_RATE_WINDOW` seconds (default 60 per 60). Over the limit the
API returns `429 RATE_LIMITED` with `Retry-After`. Polling is not limited. The
counter is shared through Redis; without Redis each process counts alone.

## Where API runs execute

Queued runs run on the worker. See
[Deploy with Compose](../operate/deploy.md#workers-and-the-queue) for
running workers as their own processes.
