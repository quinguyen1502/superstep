import re
import httpx
from ...core import config
from ...core.errors import AppError
from .base import ToolFailure, request
from .channel import ChannelTools


class TelegramTools(ChannelTools):
    id = "telegram"
    settings_schema = {"type": "object", "properties": {"channel_id": {"type": "string", "resource_kind": "telegram"}, "chat_id": {"type": "string"}}}

    def validate_target(self, settings):
        if not re.fullmatch(r"-?\d{1,20}", str(settings.get("chat_id", ""))):
            raise AppError("MCP_CONFIG_INVALID", field="settings.chat_id")

    def tools(self, settings):
        return [{"name": "send_message", "description": "Send plain text to the chat configured on this connection. Unknown outcomes are never automatically resent.",
            "input_schema": {"type": "object", "additionalProperties": False, "required": ["text"], "properties": {
                "text": {"type": "string", "minLength": 1, "maxLength": 4000},
                "reply_to_message_id": {"type": "integer", "minimum": 1}}}}]

    def execute(self, uid, settings, secrets, tool, args, key, allow_org=True):
        channel = self.authorize(uid, settings, allow_org)
        values = self.channels.secrets(channel)
        payload = {"chat_id": settings["chat_id"], "text": args["text"], "disable_web_page_preview": True}
        if args.get("reply_to_message_id"):
            payload["reply_parameters"] = {"message_id": args["reply_to_message_id"], "allow_sending_without_reply": True}
        try: response = request("POST", f"{config.telegram_api_url()}/bot{values['bot_token']}/sendMessage", json=payload)
        except httpx.HTTPError: raise ToolFailure("unknown") from None
        if response.status_code == 408 or response.status_code >= 500: raise ToolFailure("unknown")
        if not 200 <= response.status_code < 300: raise ToolFailure()
        try:
            data = response.json()
            if data.get("ok") is False: raise ToolFailure("unknown" if int(data.get("error_code", 0)) >= 500 else "failed")
            if data.get("ok") is not True: raise ValueError()
            result = data["result"]
            if not isinstance(result["message_id"], int): raise ValueError()
            return {"outcome": "confirmed", "operation_id": key, "chat_id": settings["chat_id"], "message_id": result["message_id"]}
        except (ValueError, KeyError, TypeError, AttributeError): raise ToolFailure("unknown") from None
