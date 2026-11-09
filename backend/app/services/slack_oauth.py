"""Add to Slack: OAuth v2 app distribution for approval channels.

start(uid, scope)  -> Slack authorize URL; `state` is HMAC-signed (user, scope, expiry, nonce) so a callback can't be forged.
finish(code, state) -> exchanges the code (oauth.v2.access) and saves the workspace as a Slack connection of that user,
                      with the app's signing secret (one Slack app, one signing secret, any number of workspaces)."""
from __future__ import annotations
import base64, hashlib, hmac, json, secrets, time
from urllib.parse import urlencode
from ..core import config, crypto
from ..core.errors import AppError
from .access import AccessService
from .channel_service import ChannelService

STATE_TTL = 600  # s


def configured() -> bool:
    return bool(config.slack_client_id() and config.slack_client_secret() and config.slack_signing_secret() and config.public_url())


def redirect_uri() -> str: return f"{config.public_url()}/api/approvals/slack/oauth/callback"


def _sign(body: bytes) -> str: return hmac.new(crypto.derive_key("slack-oauth-state"), body, hashlib.sha256).hexdigest()


def make_state(uid: str, scope: str, now: float | None = None) -> str:
    body = base64.urlsafe_b64encode(json.dumps({"u": uid, "s": scope, "e": int((now or time.time()) + STATE_TTL),
                                                 "n": secrets.token_hex(8)}).encode()).decode().rstrip("=")
    return f"{body}.{_sign(body.encode())}"


def read_state(state: str) -> dict:
    try:
        body, sig = (state or "").rsplit(".", 1)
        if not hmac.compare_digest(sig, _sign(body.encode())): raise ValueError
        d = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
    except (ValueError, TypeError): raise AppError("SLACK_OAUTH_STATE_INVALID")
    if d.get("e", 0) < time.time(): raise AppError("SLACK_OAUTH_STATE_INVALID")
    return d


class SlackOAuthService:
    def __init__(self, channels: ChannelService, access: AccessService):
        self.channels, self.access = channels, access

    def info(self) -> dict:
        return {"enabled": configured(), "redirect_uri": redirect_uri() if config.public_url() else None, "scopes": config.SLACK_BOT_SCOPES}

    def start(self, uid: str, scope: str = "user") -> dict:
        if not configured(): raise AppError("SLACK_OAUTH_NOT_CONFIGURED")
        if scope not in ("user", "org"): raise AppError("CHANNEL_CONFIG_INVALID", field="scope")
        if scope == "org" and not self.channels.is_admin(uid): raise AppError("CHANNEL_ADMIN_REQUIRED")
        q = {"client_id": config.slack_client_id(), "scope": config.SLACK_BOT_SCOPES, "redirect_uri": redirect_uri(), "state": make_state(uid, scope)}
        return {"url": f"{config.slack_oauth_url()}?{urlencode(q)}"}

    def finish(self, code: str, state: str) -> dict:
        if not configured(): raise AppError("SLACK_OAUTH_NOT_CONFIGURED")
        st = read_state(state)
        if self.access.role(st["u"]) is None: raise AppError("SLACK_OAUTH_STATE_INVALID")  # account gone or deactivated
        if not code: raise AppError("SLACK_OAUTH_FAILED", reason="no code")
        data = self.channels.adapter("slack").oauth_access(code, redirect_uri())
        token, team = data.get("access_token") or "", data.get("team") or {}
        if not token.startswith("xoxb-"): raise AppError("SLACK_OAUTH_FAILED", reason="no bot token")
        return self.channels.create(st["u"], {"kind": "slack", "scope": st["s"], "name": team.get("name"),
                                              "bot_token": token, "signing_secret": config.slack_signing_secret()})
