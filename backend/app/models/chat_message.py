from typing import Optional
from sqlalchemy import Float, Index, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class ChatMessage(Base):
    """A chat message that matched a chat trigger: the dedupe record, the run it started and
    where to reply. Messages that match no trigger are not stored."""
    __tablename__ = "chat_messages"
    __table_args__ = (Index("uq_chat_messages_key", "channel_id", "key", unique=True),)  # a platform retry starts nothing new
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    channel_id: Mapped[str] = mapped_column(Text, nullable=False)
    key: Mapped[str] = mapped_column(Text, nullable=False)  # Slack event_id / Telegram update_id
    trigger_id: Mapped[str] = mapped_column(Text, index=True)
    workflow_id: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # slack | telegram
    team: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")  # Slack workspace; "" elsewhere
    sender: Mapped[str] = mapped_column(Text, nullable=False)  # platform user id
    text: Mapped[str] = mapped_column(Text, nullable=False)  # after the command word
    ref: Mapped[str] = mapped_column(Text, nullable=False)  # JSON: where replies go (adapter-specific)
    status: Mapped[str] = mapped_column(Text, nullable=False)  # queued | checking | started | refused
    code: Mapped[Optional[str]] = mapped_column(Text)  # why it was refused
    run_id: Mapped[Optional[str]] = mapped_column(Text, index=True)
    replied: Mapped[Optional[str]] = mapped_column(Text)  # the last settled state replied ("ok", "waiting:<node>", ...): once each
    created: Mapped[float] = mapped_column(Float, nullable=False)
