"""Slack: chat.postMessage with Block Kit buttons; interactivity callbacks verified with the app's signing secret."""
import hashlib, hmac, json, re, time
from typing import Optional
from urllib.parse import parse_qs
from ...core import config
from ...core.errors import AppError
from .base import ApprovalChannel, ApprovalMessage, Callback, IncomingMessage

MAX_SKEW = 300  # s; Slack's recommendation against replays


class SlackChannel(ApprovalChannel):
    kind = "slack"
    label = "Slack"
    fields = ("bot_token", "signing_secret")
    patterns = {"bot_token": r"xoxb-[\w-]{8,}", "signing_secret": r"[0-9a-f]{16,128}"}
    identity_pattern = r"[UW][A-Z0-9]{2,20}"
    hint_field = "bot_token"
    per_team = True         # a member id is only meaningful inside its workspace (team_id)
    shared_callback = True  # one Request URL for every workspace: /api/approvals/callback/slack, routed by team.id
    chat = True

    place_pattern = r"[CG][A-Z0-9]{2,20}"  # public / private channel id
    chat_scopes = ("app_mentions:read", "im:history")  # chat triggers: mentions in channels, direct messages
    events_path = "/api/channels/events/slack"  # Event Subscriptions Request URL, one for every workspace (routed by team_id)

    def _post(self, secrets: dict, method: str, payload: dict):
        r, data = self.call("POST", f"{config.slack_api_url()}/{method}", json=payload,
                            headers={"Authorization": f"Bearer {secrets['bot_token']}", "Content-Type": "application/json; charset=utf-8"})
        if not data.get("ok"): raise AppError("CHANNEL_API_FAILED", kind=self.label, reason=str(data.get("error") or "not ok"))
        return r, data

    def _api(self, secrets: dict, method: str, payload: dict) -> dict: return self._post(secrets, method, payload)[1]

    def oauth_access(self, code: str, redirect_uri: str) -> dict:
        """Add to Slack: exchange the OAuth code for the workspace's bot token (oauth.v2.access)."""
        _, data = self.call("POST", f"{config.slack_api_url()}/oauth.v2.access", data={"code": code, "redirect_uri": redirect_uri},
                            auth=(config.slack_client_id(), config.slack_client_secret()))
        if not data.get("ok"): raise AppError("SLACK_OAUTH_FAILED", reason=str(data.get("error") or "not ok"))
        return data

    @staticmethod
    def _blocks(msg: ApprovalMessage) -> list[dict]:
        text = f"*{msg.title}*\n" + "\n".join(msg.lines) + (f"\n<{msg.link}|{msg.open_label}>" if msg.link else "")
        return [{"type": "section", "text": {"type": "mrkdwn", "text": text[:2900]}},
                {"type": "actions", "block_id": "studio_approval", "elements": [
                    {"type": "button", "action_id": "approve", "style": "primary", "text": {"type": "plain_text", "text": msg.approve_label}, "value": msg.approve_token},
                    {"type": "button", "action_id": "reject", "style": "danger", "text": {"type": "plain_text", "text": msg.reject_label}, "value": msg.reject_token}]}]

    def describe(self, secrets):
        r, d = self._post(secrets, "auth.test", {})
        granted = r.headers.get("x-oauth-scopes")  # Slack lists the token's scopes on every Web API response
        return {"name": d.get("team") or None, "team_id": d.get("team_id") or None,
                "scopes": None if granted is None else sorted(x.strip() for x in granted.split(",") if x.strip())}

    @staticmethod
    def _payload(body: bytes) -> dict:
        try: p = json.loads(parse_qs(body.decode()).get("payload", ["{}"])[0])
        except (ValueError, UnicodeDecodeError): return {}
        return p if isinstance(p, dict) else {}

    @staticmethod
    def _event(body: bytes) -> dict:
        try: p = json.loads(body)
        except (ValueError, UnicodeDecodeError): return {}
        return p if isinstance(p, dict) else {}

    def route_key(self, body):
        """Interactivity posts a form with the payload's team.id; the Events API posts JSON with team_id."""
        team = self._payload(body).get("team") or {}
        if isinstance(team, dict) and team.get("id"): return str(team["id"])
        return str(self._event(body).get("team_id") or "") or None

    def send_request(self, secrets, target, msg):
        data = self._api(secrets, "chat.postMessage", {"channel": target, "text": msg.title, "blocks": self._blocks(msg)})
        return {"channel": data.get("channel") or target, "ts": data["ts"]}

    def verify(self, secrets, headers, body):
        ts, sig = headers.get("x-slack-request-timestamp", ""), headers.get("x-slack-signature", "")
        try: fresh = abs(time.time() - int(ts)) <= MAX_SKEW
        except ValueError: fresh = False
        mine = "v0=" + hmac.new(secrets["signing_secret"].encode(), f"v0:{ts}:".encode() + body, hashlib.sha256).hexdigest()
        if not (fresh and hmac.compare_digest(mine, sig)): raise AppError("CHANNEL_SIGNATURE_INVALID")

    def handle_callback(self, body) -> Optional[Callback]:
        p = self._payload(body)
        acts = p.get("actions") or []
        if p.get("type") != "block_actions" or not acts or acts[0].get("action_id") not in ("approve", "reject"): return None
        return Callback(str(acts[0].get("value") or ""), str((p.get("user") or {}).get("id") or ""), {"response_url": p.get("response_url")})

    def acknowledge(self, secrets, cb, text, accepted):
        url = cb.context.get("response_url")
        if accepted or not url or not url.startswith("https://hooks.slack.com/"): return  # only Slack's own response URLs
        try: self.call("POST", url, json={"response_type": "ephemeral", "replace_original": False, "text": text})
        except AppError: pass

    def update(self, secrets, ref, text):
        self._api(secrets, "chat.update", {"channel": ref["channel"], "ts": ref["ts"], "text": text,
                                           "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": text[:2900]}}]})

    # ---- chat triggers: app_mention in channels, message.im in direct messages ----
    def handle_message(self, body) -> Optional[IncomingMessage]:
        p = self._event(body); e = p.get("event") if p.get("type") == "event_callback" else None
        if not isinstance(e, dict): return None
        dm = e.get("type") == "message" and e.get("channel_type") == "im"
        if not (dm or e.get("type") == "app_mention") or e.get("bot_id") or e.get("subtype") or not e.get("user") or not isinstance(e.get("text"), str):
            return None  # bots (our own replies too), edits, joins, files
        bot = next((a.get("user_id") for a in p.get("authorizations") or [] if isinstance(a, dict) and a.get("user_id")), None)
        text = e["text"].replace(f"<@{bot}>", " ") if bot else re.sub(r"^\s*<@[A-Z0-9]+>", " ", e["text"])
        channel = str(e.get("channel") or "")
        return IncomingMessage(str(p.get("team_id") or ""), "dm" if dm else channel, str(e["user"]), text.strip(), str(p.get("event_id") or ""),
                               {"channel": channel, **({} if dm else {"thread_ts": e.get("thread_ts") or e.get("ts")})})

    def event_challenge(self, body):
        p = self._event(body); ch = p.get("challenge")
        return ch if p.get("type") == "url_verification" and isinstance(ch, str) and len(ch) <= 200 else None

    def reply(self, secrets, ref, text):
        self._api(secrets, "chat.postMessage", {**ref, "text": text[:3900]})

    def reply_private(self, secrets, ref, sender, text):
        self._api(secrets, "chat.postEphemeral", {**ref, "user": sender, "text": text[:3900]})

    def send_dm(self, secrets, external_id, text):
        self._api(secrets, "chat.postMessage", {"channel": external_id, "text": text})  # a user id opens the app DM (scope im:write)
