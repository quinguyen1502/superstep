"""Per-chat server credentials. The encrypted secret is never a public field."""
from typing import Optional
from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class ChatAppKey(Base):
    __tablename__ = "chat_app_keys"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    trigger_id: Mapped[str] = mapped_column(Text, ForeignKey("workflow_chat_triggers.id", ondelete="CASCADE"), nullable=False, index=True)
    key_id: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    secret_enc: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str] = mapped_column(Text, nullable=False)
    origins: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[float] = mapped_column(Float, nullable=False)
    revoked_at: Mapped[Optional[float]] = mapped_column(Float)
    last_used_at: Mapped[Optional[float]] = mapped_column(Float)
