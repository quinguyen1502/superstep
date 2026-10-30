from typing import Optional
from sqlalchemy import Boolean, Float, Index, Integer, LargeBinary, Text, false
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class ChatSession(Base):
    """One conversation with a workflow's chat (TASK-0084, REQ-0048, DEC-0052). Phase 1 has studio sessions of a
    signed-in builder; `channel` and `visitor` leave room for the published page and the embed (phase 2)."""
    __tablename__ = "chat_sessions"
    __table_args__ = (Index("ix_chat_sessions_workflow_owner", "workflow_id", "owner"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_id: Mapped[str] = mapped_column(Text, nullable=False)  # the workflow's web chat trigger (its settings)
    channel: Mapped[str] = mapped_column(Text, nullable=False, default="studio", server_default="studio")  # studio | web | embed
    owner: Mapped[Optional[str]] = mapped_column(Text)  # the studio user; None for an anonymous visitor (phase 2)
    visitor: Mapped[Optional[str]] = mapped_column(Text)  # an anonymous visitor's id (phase 2)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    last_run_id: Mapped[Optional[str]] = mapped_column(Text)
    created: Mapped[float] = mapped_column(Float, nullable=False)
    updated: Mapped[float] = mapped_column(Float, nullable=False, index=True)  # the retention clock


class ChatTurn(Base):
    """A message in a chat session: the person's text, or the workflow's answer for one settled state of a run
    (finished, waiting at a Human node, failed). Steps are not copied: they are read from the run's events."""
    __tablename__ = "chat_turns"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    session_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    run_id: Mapped[Optional[str]] = mapped_column(Text, index=True)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # user | assistant
    text: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    status: Mapped[str] = mapped_column(Text, nullable=False, default="ok", server_default="ok")  # ok | waiting | error | cancelled | expired | timeout
    node: Mapped[Optional[str]] = mapped_column(Text)  # the Human node a waiting turn asks for
    answered_by: Mapped[Optional[str]] = mapped_column(Text)  # visitor | reviewer, for a waiting turn
    code: Mapped[Optional[str]] = mapped_column(Text)  # the error code of a failed turn
    attachments: Mapped[Optional[str]] = mapped_column(Text)  # JSON list of chat_attachments ids, in order (DEC-0072)
    created: Mapped[float] = mapped_column(Float, nullable=False)


class ChatRating(Base):
    """One thumbs up or down on a finished answer (TASK-0162, REQ-0075, DEC-0070). The turn id is the key, so a
    second rating replaces the first."""
    __tablename__ = "chat_ratings"
    __table_args__ = (Index("ix_chat_ratings_workflow_updated", "workflow_id", "updated"),)
    turn_id: Mapped[str] = mapped_column(Text, primary_key=True)
    session_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(Text, nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)  # up | down
    comment: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")
    feedback_id: Mapped[str] = mapped_column(Text, nullable=False, default="", server_default="")  # LangSmith, once sent
    created: Mapped[float] = mapped_column(Float, nullable=False)
    updated: Mapped[float] = mapped_column(Float, nullable=False)


class ChatAttachment(Base):
    """A file a person attached to a chat message (TASK-0174, REQ-0077, DEC-0072 decision 1). The bytes live here, not in
    `chat_turns`, so listing turns never loads files. `turn_id` is None until the message is sent; an unsent upload is
    swept after an hour."""
    __tablename__ = "chat_attachments"
    __table_args__ = (Index("ix_chat_attachments_session_turn", "session_id", "turn_id"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    session_id: Mapped[str] = mapped_column(Text, nullable=False)
    turn_id: Mapped[Optional[str]] = mapped_column(Text)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # document | image
    mime: Mapped[str] = mapped_column(Text, nullable=False)
    size: Mapped[int] = mapped_column(Integer, nullable=False)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    text: Mapped[Optional[str]] = mapped_column(Text)  # a document's extracted text, capped
    text_cut: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default=false())
    created: Mapped[float] = mapped_column(Float, nullable=False, index=True)
