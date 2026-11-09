"""Link channels: e-mail and Microsoft Teams. Their messages carry Approve / Reject links to the studio's
/approve page; the person signs in there and confirms, so the studio account is the identity and no chat account is
linked. Both need STUDIO_PUBLIC_URL for the links."""
import hashlib, html
from typing import Optional
from ...core import config
from ...core.errors import AppError
from ...core.net import pinned_request, public_address
from .. import mailer
from .base import ApprovalChannel, ApprovalMessage

EMAIL_RE = r"[^@\s,]+@[^@\s,]+\.[^@\s,]+"


def links(msg: ApprovalMessage) -> tuple[str, str]:
    base = config.public_url()
    return f"{base}/approve?token={msg.approve_token}", f"{base}/approve?token={msg.reject_token}"


def _need_public_url(kind: str) -> None:
    if not config.public_url(): raise AppError("CHANNEL_API_FAILED", kind=kind, reason="STUDIO_PUBLIC_URL is not set (the links point at the studio)")


class EmailChannel(ApprovalChannel):
    """Approval e-mail through the studio's SMTP settings (SMTP_HOST, ...). Target: one or more addresses, comma-separated."""
    kind = "email"
    label = "E-mail"
    link_based = True

    def describe(self, secrets):
        _need_public_url(self.label)
        smtp = config.smtp()
        if not smtp: raise AppError("CHANNEL_API_FAILED", kind=self.label, reason="SMTP_HOST is not set")
        return {"name": smtp["sender"], "team_id": None}

    @staticmethod
    def recipients(target: str) -> list[str]:
        import re
        out = [x.strip() for x in (target or "").split(",") if x.strip()]
        if not out or any(not re.fullmatch(EMAIL_RE, x) for x in out): raise AppError("CHANNEL_CONFIG_INVALID", field="target")
        return out

    def send_request(self, secrets, target, msg: ApprovalMessage):
        to = self.recipients(target); smtp = config.smtp(); _need_public_url(self.label)
        if not smtp: raise AppError("CHANNEL_API_FAILED", kind=self.label, reason="SMTP_HOST is not set")
        yes, no = links(msg)
        text = "\n".join([msg.title, "", *msg.lines, "", f"{msg.approve_label}: {yes}", f"{msg.reject_label}: {no}"] + ([f"{msg.open_label}: {msg.link}"] if msg.link else []))
        body = (f"<h2>{html.escape(msg.title)}</h2>" + "".join(f"<p>{html.escape(x)}</p>" for x in msg.lines)
                + f'<p><a href="{html.escape(yes)}">✅ {html.escape(msg.approve_label)}</a> &nbsp; <a href="{html.escape(no)}">❌ {html.escape(msg.reject_label)}</a></p>'
                + (f'<p><a href="{html.escape(msg.link)}">{html.escape(msg.open_label)}</a></p>' if msg.link else ""))
        failed = [x for x in to if not mailer.send(smtp, x, f"[Superstep] {msg.title}", text, body)]
        if len(failed) == len(to): raise AppError("CHANNEL_API_FAILED", kind=self.label, reason="SMTP refused the message")
        return {"to": to}

    def update(self, secrets, ref, text):
        """A sent e-mail cannot change; the run history and the audit log show the outcome."""


class TeamsChannel(ApprovalChannel):
    """A Microsoft Teams channel through a Workflows webhook ("Post to a channel when a webhook request is received").
    The URL gets the same outbound guard as result webhooks (public addresses unless STUDIO_ALLOW_PRIVATE_CALLBACKS=1).
    The request is an Adaptive Card with Approve / Reject buttons that open the studio; the outcome is a second card."""
    kind = "teams"
    label = "Microsoft Teams"
    link_based = True
    target_required = False
    fields = ("webhook_url",)
    patterns = {"webhook_url": r"https?://\S{10,2000}"}  # plain http only with STUDIO_ALLOW_PRIVATE_CALLBACKS (local tests)
    hint_field = "webhook_url"

    def describe(self, secrets):
        _need_public_url(self.label)
        if not secrets["webhook_url"].startswith("https://") and not config.allow_private_callbacks(): raise AppError("CHANNEL_CONFIG_INVALID", field="webhook_url")
        public_address(secrets["webhook_url"], config.allow_private_callbacks(), "CHANNEL_CONFIG_INVALID", field="webhook_url")
        # one connection per webhook (a Teams channel), so the same owner can connect several
        return {"name": None, "team_id": hashlib.sha256(secrets["webhook_url"].encode()).hexdigest()[:16]}

    def _post(self, secrets: dict, card: dict) -> None:
        url, ip = public_address(secrets["webhook_url"], config.allow_private_callbacks(), "CHANNEL_CONFIG_INVALID", field="webhook_url")
        pinned, headers, ext = pinned_request(url, ip)
        payload = {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": {
            "type": "AdaptiveCard", "$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "version": "1.4", **card}}]}
        import httpx
        try:
            with httpx.Client(timeout=10, transport=self.transport, follow_redirects=False) as c: r = c.post(pinned, json=payload, headers=headers, extensions=ext)
        except httpx.HTTPError as e: raise AppError("CHANNEL_API_FAILED", kind=self.label, reason=type(e).__name__)
        if r.status_code >= 300: raise AppError("CHANNEL_API_FAILED", kind=self.label, reason=f"HTTP {r.status_code}")

    def send_request(self, secrets, target, msg: ApprovalMessage):
        _need_public_url(self.label); yes, no = links(msg)
        actions = [{"type": "Action.OpenUrl", "title": f"✅ {msg.approve_label}", "url": yes}, {"type": "Action.OpenUrl", "title": f"❌ {msg.reject_label}", "url": no}]
        if msg.link: actions.append({"type": "Action.OpenUrl", "title": msg.open_label, "url": msg.link})
        self._post(secrets, {"body": [{"type": "TextBlock", "text": msg.title, "weight": "Bolder", "size": "Medium", "wrap": True},
                                      *({"type": "TextBlock", "text": x, "wrap": True, "spacing": "Small"} for x in msg.lines)], "actions": actions})
        return {"posted": True}

    def update(self, secrets, ref, text):
        """Workflows webhooks cannot edit a card: the outcome is posted as a new one."""
        self._post(secrets, {"body": [{"type": "TextBlock", "text": text, "wrap": True}]})
