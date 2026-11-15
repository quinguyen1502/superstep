"""WhatsApp Cloud API: reply buttons; the webhook is signed with the Meta app secret (X-Hub-Signature-256).

WhatsApp only delivers free-form and button messages within 24 hours of the person's last message to the business
number. Outside that window, set `template_name` to an approved template with two quick-reply buttons (Approve, Reject):
the request is then sent as that template, with the question as body variable {{1}}.
"""
import hashlib, hmac, json
from typing import Optional
from ...core import config
from ...core.errors import AppError
from .base import ApprovalChannel, ApprovalMessage, Callback


class WhatsAppChannel(ApprovalChannel):
    kind = "whatsapp"
    label = "WhatsApp"
    fields = ("access_token", "phone_number_id", "app_secret", "verify_token", "template_name", "template_lang")
    optional = ("template_name", "template_lang")
    patterns = {"phone_number_id": r"\d{5,20}", "app_secret": r"[0-9a-f]{32}", "verify_token": r"[\w.~-]{8,128}",
                "template_name": r"[a-z0-9_]{1,512}", "template_lang": r"[a-z]{2,3}(_[A-Z]{2})?"}
    identity_pattern = r"\d{6,20}"  # wa_id: the phone number in international form without "+"
    hint_field = "phone_number_id"

    def _url(self, secrets: dict, path: str) -> str: return f"{config.whatsapp_api_url()}/{path.format(**secrets)}"

    def _api(self, secrets: dict, method: str, path: str, payload: Optional[dict] = None) -> dict:
        r, data = self.call(method, self._url(secrets, path), json=payload, headers={"Authorization": f"Bearer {secrets['access_token']}"})
        if r.status_code >= 400 or not isinstance(data, dict) or data.get("error"):
            err = (data or {}).get("error") if isinstance(data, dict) else None
            raise AppError("CHANNEL_API_FAILED", kind=self.label, reason=str((err or {}).get("message") or f"HTTP {r.status_code}")[:200])
        return data

    def describe(self, secrets):
        d = self._api(secrets, "GET", "{phone_number_id}?fields=display_phone_number,verified_name")
        return {"name": d.get("verified_name") or d.get("display_phone_number"), "team_id": None}

    def challenge(self, secrets, query):
        if query.get("hub.mode") == "subscribe" and hmac.compare_digest(str(query.get("hub.verify_token") or ""), secrets.get("verify_token", "")):
            return str(query.get("hub.challenge") or "")
        raise AppError("CHANNEL_SIGNATURE_INVALID")

    def _send(self, secrets: dict, to: str, body: dict) -> dict:
        res = self._api(secrets, "POST", "{phone_number_id}/messages", {"messaging_product": "whatsapp", "to": to, **body})
        return {"to": to, "message_id": ((res.get("messages") or [{}])[0]).get("id")}

    def send_request(self, secrets, target, msg: ApprovalMessage):
        text = "\n".join([f"*{msg.title}*", *msg.lines] + ([f"{msg.open_label}: {msg.link}"] if msg.link else []))
        if secrets.get("template_name"):  # works outside the 24-hour window
            return self._send(secrets, target, {"type": "template", "template": {"name": secrets["template_name"], "language": {"code": secrets.get("template_lang") or "en"},
                "components": [{"type": "body", "parameters": [{"type": "text", "text": " · ".join(msg.lines)[:1000]}]},
                               *({"type": "button", "sub_type": "quick_reply", "index": str(i), "parameters": [{"type": "payload", "payload": tok}]}
                                 for i, tok in enumerate((msg.approve_token, msg.reject_token)))]}})
        return self._send(secrets, target, {"type": "interactive", "interactive": {"type": "button", "body": {"text": text[:1024]}, "action": {"buttons": [
            {"type": "reply", "reply": {"id": msg.approve_token, "title": f"✅ {msg.approve_label}"[:20]}},
            {"type": "reply", "reply": {"id": msg.reject_token, "title": f"❌ {msg.reject_label}"[:20]}}]}}})

    def verify(self, secrets, headers, body):
        want = "sha256=" + hmac.new(secrets.get("app_secret", "").encode(), body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(headers.get("x-hub-signature-256", ""), want): raise AppError("CHANNEL_SIGNATURE_INVALID")

    def handle_callback(self, body) -> Optional[Callback]:
        """A reply-button press (`interactive.button_reply.id`) or a template quick reply (`button.payload`)."""
        try: msgs = [m for e in json.loads(body).get("entry") or [] for ch in e.get("changes") or [] for m in (ch.get("value") or {}).get("messages") or []]
        except (ValueError, AttributeError, TypeError): return None
        for m in msgs:
            tok = ((m.get("interactive") or {}).get("button_reply") or {}).get("id") if m.get("type") == "interactive" else \
                (m.get("button") or {}).get("payload") if m.get("type") == "button" else None
            if tok: return Callback(str(tok), str(m.get("from") or ""), {"from": m.get("from")})
        return None

    def acknowledge(self, secrets, cb, text, accepted):
        if accepted: return  # update() tells the chat
        try: self._send(secrets, cb.context.get("from") or cb.external_user, {"type": "text", "text": {"body": text[:1000]}})
        except AppError: pass

    def update(self, secrets, ref, text):
        """WhatsApp cannot edit a sent message: the outcome is a reply to the request."""
        self._send(secrets, ref["to"], {"type": "text", "text": {"body": text[:1000]}, **({"context": {"message_id": ref["message_id"]}} if ref.get("message_id") else {})})

    def send_dm(self, secrets, external_id, text):
        self._send(secrets, external_id, {"type": "text", "text": {"body": text[:1000]}})  # needs the person's message in the last 24 h
