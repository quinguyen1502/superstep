from typing import Optional
from sqlalchemy import Boolean, Float, Index, LargeBinary, Text, true
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class WorkflowChatTrigger(Base):
    """A command word that starts a workflow from a Slack or Telegram message (TASK-0074, DEC-0046), or a workflow's web chat
    (TASK-0084, DEC-0052): channel_id = place = "web", command = the chat's slug for the published page (phase 2)."""
    __tablename__ = "workflow_chat_triggers"
    __table_args__ = (Index("uq_workflow_chat_triggers_command", "channel_id", "place", "command", unique=True),)  # one trigger per message
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(Text, index=True)
    owner: Mapped[str] = mapped_column(Text, nullable=False)  # the creator: needs the workflow's share right
    name: Mapped[str] = mapped_column(Text, nullable=False)
    channel_id: Mapped[str] = mapped_column(Text, index=True)  # the approval connection (Slack workspace / Telegram bot)
    place: Mapped[str] = mapped_column(Text, nullable=False)  # Slack channel id, Telegram chat id, or "dm" (direct messages to the bot)
    command: Mapped[str] = mapped_column(Text, nullable=False)  # lower-case word
    input_field: Mapped[str] = mapped_column(Text, nullable=False)  # state field that gets the message text
    reply_field: Mapped[str] = mapped_column(Text, nullable=False)  # state field the reply shows
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    note: Mapped[Optional[str]] = mapped_column(Text)  # why it stopped: access | channel | scopes
    last_message: Mapped[Optional[float]] = mapped_column(Float)
    last_run_id: Mapped[Optional[str]] = mapped_column(Text)
    created: Mapped[float] = mapped_column(Float, nullable=False)
    settings: Mapped[Optional[str]] = mapped_column(Text)  # JSON: the web chat's settings (TASK-0084); None for Slack/Telegram


class ChatLogo(Base):
    """A published chat's logo (TASK-0145, REQ-0074): one PNG, JPEG or WebP image per web chat trigger. Its settings keep
    the image's hash as `logo`, which versions the logo's address."""
    __tablename__ = "chat_logos"
    trigger_id: Mapped[str] = mapped_column(Text, primary_key=True)
    mime: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    created: Mapped[float] = mapped_column(Float, nullable=False)
