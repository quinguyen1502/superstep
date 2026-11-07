# Expose a local studio

Slack, Telegram and WhatsApp call the studio back over the internet, and
Telegram accepts only HTTPS. A studio on your machine needs a public HTTPS
address for that: a tunnel. The studio learns that address from one variable,
`STUDIO_PUBLIC_URL`.

!!! warning "A tunnel publishes the whole studio"
    Everyone who has the address reaches the sign-in page and the API, not only
    the callback paths. Do not tunnel a studio that still has the demo account
    (`admin@example.com` / `admin123`) or the placeholder `JWT_SECRET`. Use real
    accounts and secrets (see [Accounts and security](accounts.md)), restrict the
    tunnel when the provider allows it, and stop it when you are done. Never turn
    off callback signature checks to make a callback work.

## Pick the local port

The tunnel must point at the process that answers `/api`.

| How you run the studio | Local address to tunnel |
| --- | --- |
| Development (`uvicorn` API) | `http://localhost:8000` |
| Docker Compose (nginx entry) | `http://localhost:8080` (or your `WEB_PORT`) |
| Single image | `http://localhost:8000` (or your `PORT`) |

The development API serves only `/api`. Pages opened from a public link (the
**Add to Slack** return page, e-mail and Teams links) need the Compose or image
entry, which also serves the web app. The examples below use 8000.

## Temporary or stable address

A quick tunnel gets a new random address each time it starts. After every
restart you have to update `STUDIO_PUBLIC_URL` and the provider settings again.
Use a stable address (named Cloudflare tunnel, ngrok dev or reserved domain,
persistent dev tunnel) for anything you keep for more than one session.

## Cloudflare Tunnel

Quick tunnel, no account, temporary `trycloudflare.com` address
([Cloudflare docs](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)):

```bash
cloudflared tunnel --url http://localhost:8000
```

Anyone with the URL can reach the studio, and it stops when `cloudflared`
stops. Quick tunnels do not support Server-Sent Events, so live run updates in a
browser opened through the tunnel may not stream; callbacks are plain requests
and work.

For a stable hostname on a domain in your Cloudflare account, create a
locally-managed named tunnel
([Cloudflare docs](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/create-local-tunnel/)):

```bash
cloudflared tunnel login
cloudflared tunnel create studio
```

Write `~/.cloudflared/config.yml` with the UUID and credentials file that
`create` printed:

```yaml
url: http://localhost:8000
tunnel: <Tunnel-UUID>
credentials-file: /home/you/.cloudflared/<Tunnel-UUID>.json
```

Then route a hostname and run it:

```bash
cloudflared tunnel route dns studio studio.example.com
cloudflared tunnel run studio
```

Cloudflare Access can put a login in front of the hostname; leave the callback
paths under `/api/approvals/callback/` reachable for the providers.

## ngrok

Install the agent, add your authtoken once, then start an endpoint
([ngrok docs](https://ngrok.com/docs/getting-started/)):

```bash
ngrok config add-authtoken <your-token>
ngrok http 8000
```

Each account has a dev domain that `ngrok http` reuses across restarts. To use a
specific reserved or custom domain:

```bash
ngrok http 8000 --url https://studio.example.ngrok.app
```

## Microsoft Dev Tunnels

Sign in with a Microsoft, Microsoft Entra ID or GitHub account
([Dev Tunnels docs](https://learn.microsoft.com/en-us/azure/developer/dev-tunnels/get-started)).
Tunnels are private by default; providers cannot sign in, so callbacks need
anonymous access.

Temporary tunnel, deleted when the command stops:

```bash
devtunnel user login
devtunnel host -p 8000 --allow-anonymous
```

Persistent tunnel that keeps its address:

```bash
devtunnel create --allow-anonymous
devtunnel port create -p 8000
devtunnel host
```

Use the `https://…devtunnels.ms` address printed for the port.

## Set the address and restart

1. Copy the HTTPS origin the tunnel prints, without a path or trailing slash,
   for example `https://studio.example.com`.
2. Set it where the API reads its environment (your shell, `.env` or Compose
   file):

    ```bash
    STUDIO_PUBLIC_URL=https://studio.example.com
    ```

3. Restart the API and worker. In **Settings → Channels** the "STUDIO_PUBLIC_URL
   is not set" note disappears.

## Update provider callbacks

The address is part of every callback, so update the providers whenever it
changes (see [Approval channels](channels.md)):

| Provider | Where | URL |
| --- | --- | --- |
| Slack | **Interactivity & Shortcuts** request URL | `{STUDIO_PUBLIC_URL}/api/approvals/callback/slack` |
| Slack (Add to Slack) | OAuth redirect URL | `{STUDIO_PUBLIC_URL}/api/approvals/slack/oauth/callback` |
| Telegram | Press **Register webhook** on the connection again | `{STUDIO_PUBLIC_URL}/api/approvals/callback/telegram/{channel_id}` |
| WhatsApp | Meta app webhook callback URL | `{STUDIO_PUBLIC_URL}/api/approvals/callback/whatsapp/{channel_id}` |

[Chat triggers](../run/chat-triggers.md) use the same Slack events URL and
Telegram webhook, so re-register them too.

## Check it works

- `curl https://studio.example.com/api/health` from another network returns OK.
- **Test connection** on the connection in **Settings → Channels** delivers a message.
- Slack's request URL check passes; Telegram's `getWebhookInfo` shows the new URL
  without a recent error; Meta's webhook verification succeeds.
- Approve a test request and confirm the run continues.
