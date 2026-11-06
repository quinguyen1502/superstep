"""Durable browser authority/order metadata; never page state, arguments or raw credentials."""
from typing import Optional
from sqlalchemy import Boolean, Float, ForeignKey, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class BrowserSession(Base):
    __tablename__ = 'browser_sessions'
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner: Mapped[str] = mapped_column(Text, nullable=False, index=True)  # retain minimal pending cleanup after account deletion
    principal_id: Mapped[str] = mapped_column(Text, nullable=False)
    conversation_id: Mapped[Optional[str]] = mapped_column(Text, index=True)  # chat-driven cross-turn binding (DEC-0085)
    run_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    group_id: Mapped[str] = mapped_column(Text, nullable=False)
    connection_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    configuration: Mapped[str] = mapped_column(Text, nullable=False)
    lease_generation: Mapped[int] = mapped_column(Integer, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    next_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    executing_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wire_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    worker_id: Mapped[Optional[str]] = mapped_column(Text)
    control_secret: Mapped[Optional[str]] = mapped_column(Text)  # encrypted remote cleanup authority only
    cleanup_pending: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created: Mapped[float] = mapped_column(Float, nullable=False)
    expires: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    touched: Mapped[float] = mapped_column(Float, nullable=False)


class BrowserCommand(Base):
    __tablename__ = 'browser_commands'
    __table_args__ = (UniqueConstraint('session_id', 'position', name='uq_browser_commands_position'),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    session_id: Mapped[str] = mapped_column(Text, ForeignKey('browser_sessions.id', ondelete='CASCADE'), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    body_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, default='pending')
    started: Mapped[Optional[float]] = mapped_column(Float)
    ended: Mapped[Optional[float]] = mapped_column(Float)


class BrowserCapacity(Base):
    __tablename__ = 'browser_capacity'
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    epoch: Mapped[int] = mapped_column(Integer, nullable=False)
