"""Managed sends using approval-channel secrets; acknowledgements confirm acceptance, not delivery."""
import hashlib, html, json, re
import httpx
from ...core import config, smtp
from ...core.errors import AppError
from ...engine.emails import message_id
from ..email_quota import take_email_quota
from .base import ToolFailure, request
from .channel import ChannelTools

TEXT = {"type": "string", "minLength": 1, "maxLength": 4000}


def schema(kind, **properties):
    return {"type": "object", "properties": {"channel_id": {"type": "string", "resource_kind": kind}, **properties}}


def tool_schema(name, description, properties=None):
    return [{"name": name, "description": description, "input_schema": {"type": "object", "additionalProperties": False,
        "required": ["text"], "properties": {"text": TEXT, **(properties or {})}}}]


def post(url, payload, headers=None):
    try: response = request("POST", url, json=payload, headers=headers or {}, max_bytes=65536)
    except httpx.HTTPError: raise ToolFailure("unknown") from None
    if response.status_code == 408 or response.status_code >= 500: raise ToolFailure("unknown")
    if not 200 <= response.status_code < 300: raise ToolFailure()
    return response


def data_of(response):
    try:
        data = response.json()
        if response.status_code == 202 or not isinstance(data, dict): raise ValueError()
        return data
    except (ValueError, TypeError): raise ToolFailure("unknown") from None


class SlackTools(ChannelTools):
    id = "slack"
    settings_schema = schema(id, destination_channel={"type": "string"})

    def validate_target(self, settings):
        if not isinstance(settings.get("destination_channel"), str) or not re.fullmatch(r"[CGD][A-Z0-9]{2,20}", settings["destination_channel"]):
            raise AppError("MCP_CONFIG_INVALID", field="settings.destination_channel")

    def tools(self, settings):
        return tool_schema("send_message", "Submit plain text to the configured Slack conversation. Unknown outcomes are never resent.",
            {"thread_ts": {"type": "string", "pattern": r"^\d{1,20}\.\d{1,10}$"}})

    def execute(self, uid, settings, secrets, tool, args, key, allow_org=True):
        channel = self.authorize(uid, settings, allow_org); values = self.channels.secrets(channel)
        payload = {"channel": settings["destination_channel"], "text": html.escape(args["text"], quote=False),
            "mrkdwn": False, "parse": "none", "unfurl_links": False, "unfurl_media": False}
        if args.get("thread_ts"): payload["thread_ts"] = args["thread_ts"]
        data = data_of(post(f"{config.slack_api_url()}/chat.postMessage", payload, {"Authorization": f"Bearer {values['bot_token']}"}))
        if data.get("ok") is False: raise ToolFailure("unknown" if data.get("error") in {"internal_error", "fatal_error", "request_timeout"} else "failed")
        if data.get("ok") is not True or data.get("channel") != settings["destination_channel"] or not isinstance(data.get("ts"), str) or not re.fullmatch(r"\d{1,20}\.\d{1,10}", data["ts"]):
            raise ToolFailure("unknown")
        return {"outcome": "confirmed", "operation_id": key, "delivery": "accepted", "channel": data["channel"], "ts": data["ts"]}


class WhatsAppTools(ChannelTools):
    id = "whatsapp"
    settings_schema = schema(id, recipient_phone={"type": "string"})

    def validate_target(self, settings):
        if not isinstance(settings.get("recipient_phone"), str) or not re.fullmatch(r"[1-9]\d{5,19}", settings["recipient_phone"]):
            raise AppError("MCP_CONFIG_INVALID", field="settings.recipient_phone")

    def tools(self, settings):
        return tool_schema("send_message", "Submit WhatsApp text to the configured recipient within the customer-service window. Does not use approval templates.")

    def execute(self, uid, settings, secrets, tool, args, key, allow_org=True):
        channel = self.authorize(uid, settings, allow_org); values = self.channels.secrets(channel)
        data = data_of(post(f"{config.whatsapp_api_url()}/{values['phone_number_id']}/messages",
            {"messaging_product": "whatsapp", "to": settings["recipient_phone"], "type": "text", "text": {"body": args["text"], "preview_url": False}},
            {"Authorization": f"Bearer {values['access_token']}"}))
        if data.get("error"): raise ToolFailure("unknown")  # a 2xx error body is not a confirmed send
        messages = data.get("messages")
        mid = messages[0].get("id") if isinstance(messages, list) and len(messages) == 1 and isinstance(messages[0], dict) else None
        if not isinstance(mid, str) or not 1 <= len(mid) <= 512: raise ToolFailure("unknown")
        return {"outcome": "confirmed", "operation_id": key, "delivery": "accepted", "to": settings["recipient_phone"], "message_id": mid}


class EmailTools(ChannelTools):
    id = "email"
    settings_schema = schema(id, recipients={"type": "string"})

    def __init__(self, channels, quota=None):
        super().__init__(channels); self.quota = quota

    @staticmethod
    def recipients(settings):
        value = settings.get("recipients")
        if not isinstance(value, str) or len(value) > 2000 or any(c in value for c in "\r\n"): raise AppError("MCP_CONFIG_INVALID", field="settings.recipients")
        addresses = smtp.addresses(value)
        if not 1 <= len(addresses) <= 10 or smtp.invalid(addresses) or len(set(addresses)) != len(addresses):
            raise AppError("MCP_CONFIG_INVALID", field="settings.recipients")
        return addresses

    def validate_target(self, settings): self.recipients(settings)

    def tools(self, settings):
        return tool_schema("send_email", "Submit plain-text email through the existing channel's studio SMTP configuration to fixed recipients. Acceptance is not delivery.",
            {"subject": {"type": "string", "maxLength": 200}})

    def execute(self, uid, settings, secrets, tool, args, key, allow_org=True):
        channel = self.authorize(uid, settings, allow_org); recipients = self.recipients(settings)
        server = config.smtp()
        if not server: raise AppError("CHANNEL_API_FAILED", kind="Email", reason="SMTP_HOST is not set")
        take_email_quota(self.quota, uid, len(recipients))
        digest = hashlib.sha256(json.dumps([uid, channel.id, key]).encode()).hexdigest()
        mid = message_id("studio-" + digest, server["sender"])
        message = smtp.message(server, recipients, args.get("subject") or "Superstep", args["text"], message_id=mid)
        try:
            refused = smtp.deliver(server, message, recipients)
        except AppError as error:
            raise ToolFailure("failed" if error.code in {"EMAIL_HOST_BLOCKED", "EMAIL_AUTH_FAILED"} else "unknown") from None
        if refused: raise ToolFailure("unknown")  # some recipients may already have accepted the message
        return {"outcome": "confirmed", "operation_id": key, "delivery": "accepted", "to": recipients, "message_id": mid}


class TeamsTools(ChannelTools):
    id = "teams"
    settings_schema = schema(id)

    def tools(self, settings):
        return tool_schema("send_message", "Submit text through the configured Microsoft Teams Workflows webhook. Acceptance does not confirm downstream delivery.")

    def execute(self, uid, settings, secrets, tool, args, key, allow_org=True):
        channel = self.authorize(uid, settings, allow_org); values = self.channels.secrets(channel)
        post(values["webhook_url"], {"type": "message", "attachments": [{"contentType": "application/vnd.microsoft.card.adaptive", "content": {
            "type": "AdaptiveCard", "$schema": "http://adaptivecards.io/schemas/adaptive-card.json", "version": "1.4",
            "body": [{"type": "TextBlock", "text": args["text"], "wrap": True}]}}]})
        return {"outcome": "confirmed", "operation_id": key, "delivery": "accepted"}
