"""Signed JSON event source. No outbound delivery, arbitrary URL or implicit studio identity."""
import json
from .base import ApprovalChannel, IncomingMessage
from ..webhooks import verify_signature
from ...core.errors import AppError


class WebhookChannel(ApprovalChannel):
    kind = "webhook"
    label = "Signed JSON webhook"
    fields = ("signing_secret",)
    patterns = {"signing_secret": r"[A-Za-z0-9_-]{32,256}"}
    hint_field = "signing_secret"
    chat = True
    events_only = True
    place_pattern = r"[A-Za-z0-9_-]{1,64}"

    def verify(self, secrets, headers, body):
        try: valid = verify_signature(secrets["signing_secret"], headers.get("x-studio-signature", ""), body)
        except (ValueError, TypeError): valid = False
        if not valid:
            raise AppError("CHANNEL_SIGNATURE_INVALID")

    def handle_callback(self, body): return None

    def handle_message(self, body):
        try: value = json.loads(body)
        except (ValueError, UnicodeDecodeError, RecursionError): return None
        if not isinstance(value, dict): return None
        for key in ("id", "type", "place", "sender"):
            if not isinstance(value.get(key), str) or not 1 <= len(value[key]) <= 200: return None
        if not isinstance(value.get("data"), dict) or not isinstance(value.get("time"), str) or len(value["time"]) > 80: return None
        text = value["data"].get("text", "")
        if not isinstance(text, str): return None
        return IncomingMessage("", value["place"], value["sender"], text, value["id"], {},
                               {"type": value["type"], "time": value["time"], "data": value["data"]})
