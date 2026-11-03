"""Telegram: bot sendMessage with an inline keyboard; the webhook is authenticated by the secret_token header."""
import hmac, json, re, secrets as pysecrets
from datetime import datetime, timezone
from typing import Optional
from ...core import config
from ...core.errors import AppError
from .base import ApprovalChannel, ApprovalMessage, Callback, IncomingMessage


class TelegramChannel(ApprovalChannel):
    kind = "telegram"
    label = "Telegram"
    fields = ("bot_token", "webhook_secret")
    optional = ("webhook_secret",)
    patterns = {"bot_token": r"\d{3,15}:[\w-]{20,64}", "webhook_secret": r"[A-Za-z0-9_-]{16,256}"}
    identity_pattern = r"\d{1,20}"
    hint_field = "bot_token"
    chat = True  # messages arrive on the same webhook as button presses (TASK-0074)
    place_pattern = r"-?\d{1,20}"  # chat id; groups are negative

    def prepare(self, values):
        out = super().prepare(values)
        out.setdefault("webhook_secret", pysecrets.token_urlsafe(32))  # generated when the owner leaves it empty
        return out

    def _api(self, secrets: dict, method: str, payload: dict) -> dict:
        _, data = self.call("POST", f"{config.telegram_api_url()}/bot{secrets['bot_token']}/{method}", json=payload)
        if not data.get("ok"): raise AppError("CHANNEL_API_FAILED", kind=self.label, reason=str(data.get("description") or "not ok")[:200])
        return data.get("result")

    def describe(self, secrets):
        me = self._api(secrets, "getMe", {}) or {}
        return {"name": f"@{me['username']}" if me.get("username") else None, "team_id": str(me["id"]) if me.get("id") else None}

    def register(self, secrets, callback_url):
        self._api(secrets, "setWebhook", {"url": callback_url, "secret_token": secrets["webhook_secret"], "allowed_updates": ["callback_query", "message"]})
        return {"registered": True, "manual": False}

    def send_request(self, secrets, target, msg: ApprovalMessage):
        text = "\n".join([msg.title, *msg.lines] + ([f"{msg.open_label}: {msg.link}"] if msg.link else []))[:4000]
        res = self._api(secrets, "sendMessage", {"chat_id": target, "text": text, "disable_web_page_preview": True, "reply_markup": {"inline_keyboard": [[
            {"text": f"✅ {msg.approve_label}", "callback_data": msg.approve_token}, {"text": f"❌ {msg.reject_label}", "callback_data": msg.reject_token}]]}})
        return {"chat_id": (res.get("chat") or {}).get("id", target), "message_id": res["message_id"]}

    def verify(self, secrets, headers, body):
        if not hmac.compare_digest(headers.get("x-telegram-bot-api-secret-token", ""), secrets.get("webhook_secret", "")):
            raise AppError("CHANNEL_SIGNATURE_INVALID")

    def handle_callback(self, body) -> Optional[Callback]:
        try: q = json.loads(body).get("callback_query")
        except ValueError: return None
        if not isinstance(q, dict) or not q.get("data"): return None
        return Callback(str(q["data"]), str((q.get("from") or {}).get("id") or ""), {"callback_query_id": q.get("id")})

    def acknowledge(self, secrets, cb, text, accepted):
        try: self._api(secrets, "answerCallbackQuery", {"callback_query_id": cb.context.get("callback_query_id"), "text": text[:200], "show_alert": not accepted})
        except AppError: pass

    def update(self, secrets, ref, text):
        self._api(secrets, "editMessageText", {"chat_id": ref["chat_id"], "message_id": ref["message_id"], "text": text[:4000]})

    def send_dm(self, secrets, external_id, text):
        self._api(secrets, "sendMessage", {"chat_id": external_id, "text": text})  # works once the user pressed Start in the bot chat

    # ---- chat triggers (TASK-0075): messages to the bot, in a private chat or a group ----
    def handle_message(self, body) -> Optional[IncomingMessage]:
        try: u = json.loads(body)
        except (ValueError, UnicodeDecodeError): return None
        m = u.get("message") if isinstance(u, dict) else None
        if not isinstance(m, dict) or not isinstance(m.get("text"), str) or (m.get("from") or {}).get("is_bot") or not (m.get("from") or {}).get("id"):
            return None
        chat = m.get("chat") or {}
        text = re.sub(r"^@\w+\s+", "", m["text"].strip())          # "@studio_bot leave ..."
        text = re.sub(r"^/([\w-]+)@\w+", r"/\1", text)             # "/leave@studio_bot ..." (commands in groups)
        try: stamp = datetime.fromtimestamp(m["date"], timezone.utc).isoformat() if isinstance(m.get("date"), (int, float)) else None
        except (ValueError, OverflowError, OSError): return None
        actor = m["from"]
        name = " ".join(str(actor.get(k) or "") for k in ("first_name", "last_name")).strip() or str(actor.get("username") or "")
        return IncomingMessage("", "dm" if chat.get("type") == "private" else str(chat.get("id")), str(actor["id"]), text,
                               str(u.get("update_id")), {"chat_id": chat.get("id"), "message_id": m.get("message_id")},
                               {"time": stamp, "name": name[:200], "data": {"text": m["text"], "message_id": m.get("message_id")}})

    def reply(self, secrets, ref, text):
        self._api(secrets, "sendMessage", {"chat_id": ref["chat_id"], "text": text[:4000], "disable_web_page_preview": True,
                                           "reply_parameters": {"message_id": ref["message_id"], "allow_sending_without_reply": True}})

    def reply_private(self, secrets, ref, sender, text):
        """Telegram has no message only one member of a group sees: a direct message, which works once the sender has
        started the bot; else the reply goes to the group."""
        if str(ref["chat_id"]) != sender:
            try: self._api(secrets, "sendMessage", {"chat_id": sender, "text": text[:4000]}); return
            except AppError: pass
        self.reply(secrets, ref, text)
