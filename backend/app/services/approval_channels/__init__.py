"""Approval channel adapters. Buttons: Slack, Telegram, WhatsApp. Links to the studio: e-mail, Teams."""
from .base import ApprovalChannel, ApprovalMessage, Callback, IncomingMessage
from .links import EmailChannel, TeamsChannel
from .slack import SlackChannel
from .telegram import TelegramChannel
from .whatsapp import WhatsAppChannel
from .webhook import WebhookChannel

ADAPTERS: dict[str, ApprovalChannel] = {a.kind: a for a in (SlackChannel(), TelegramChannel(), WhatsAppChannel(), EmailChannel(), TeamsChannel(), WebhookChannel())}

__all__ = ["ADAPTERS", "ApprovalChannel", "ApprovalMessage", "Callback", "IncomingMessage"]
