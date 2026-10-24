# Public demo mode

`STUDIO_DEMO_MODE=true` turns an instance into a public, throw-away demo. The live demo is
https://superstep-demo.onrender.com (Render free plan, Singapore). Never turn it on for real work.

## Design: a read-only visitor of your own

The sign-in page shows **Try the demo**. It signs in with `demo@superstep.dev` and a public
password. That account is created on every boot with the global role **viewer**; each sign-in
with it gets a fresh anonymous visitor account of its own (also a viewer, with the samples shared
read-only), so a visitor's run history, chats, waiting runs and notifications are private. The
existing role rules already keep it away from credentials, knowledge bases, API tokens, MCP
servers, approval connections, creating workflows and every admin page. Demo mode adds:

| Area | In demo mode |
| --- | --- |
| Writes | The API refuses every write from the visitor except signing in and out, cancelling a run, answering a Human node, marking notifications read and starting or deleting chats in the Chat panel (`403 DEMO_READ_ONLY`). Visitors cannot save, share, rename or delete workflows, or change the account (password, preferences, linked identities). |
| Sign-up, password reset | Closed to everyone (`DEMO_READ_ONLY`), so nobody can create accounts with more rights. |
| Running | Visitors may run their **unsaved** edits in the editor. Nothing they change is stored. |
| Code nodes | Off, enforced by the server (`DEMO_CODE_DISABLED`); the editor says why. |
| HTTP Tool and Send email nodes | Refused when they run (`DEMO_NODE_DISABLED`), so a run never calls out. |
| LLM and Decision nodes | Always the offline mock model, even when `OPENAI_API_KEY` is set. No provider is called. Mock replies (and the example `lookup_order` tool) answer in the visitor's UI language, English or Vietnamese. |
| Visitor data | Visitor accounts older than `STUDIO_DEMO_VISITOR_TTL` seconds (default 86400, one day) are removed with their runs and chats, at every boot and every demo sign-in. |
| Rate limit | `STUDIO_DEMO_RUN_RATE_LIMIT` runs per client IP per minute (default 20; `RATE_LIMITED`). |
| Samples | The example, Chatbot (the chat-style one: `message` in, `answer` out, with web chat on for the Chat panel), Router and Approval flow are created and shared with the visitor on every boot, because the free plan's SQLite file is wiped when the service sleeps. |
| Banner | Every page shows a small notice: this is a demo, data resets, the first load may take about 30 s. |

The admin (`STUDIO_ADMIN_EMAILS` with a fixed `STUDIO_ADMIN_PASSWORD`) is a normal account and
is not restricted; keep that password private.

Limits, honestly: a visitor's history lives only as long as their session (signing in again
starts a new visitor), and admins see the visitor accounts in the user list. MCP and Retriever nodes have nothing to use (no servers or knowledge
bases exist). The run timeout and input size limits are the normal ones.

## Run your own demo

```bash
STUDIO_DEMO_MODE=true
STUDIO_SECRET_KEY=<random>  JWT_SECRET=<random>
STUDIO_ADMIN_EMAILS=you@example.com  STUDIO_ADMIN_PASSWORD=<random, 8+ chars, a letter and a digit>
```

On Render: a free Docker web service from this repository, with the variables above. No disk
is needed: the demo is meant to reset.
