from typing import Optional
from sqlalchemy import Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class AuditEvent(Base):
    """Administrative audit log: roles, shares, teams, ownership, deactivation, deletion, policy.
    Actor and target e-mails are copied at write time so the log survives user deletion."""
    __tablename__ = "audit_events"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    ts: Mapped[float] = mapped_column(Float, index=True)
    actor_id: Mapped[Optional[str]] = mapped_column(Text, index=True)
    actor_email: Mapped[Optional[str]] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text, index=True)      # e.g. user.role, share.add, team.member_add, workflow.transfer
    target_type: Mapped[str] = mapped_column(Text)             # user | workflow | team | policy
    target_id: Mapped[Optional[str]] = mapped_column(Text)
    target_label: Mapped[Optional[str]] = mapped_column(Text)
    details: Mapped[Optional[str]] = mapped_column(Text)       # JSON


class StudioSetting(Base):
    """Studio-wide settings edited by admins (key -> JSON value), e.g. the org-resource run-time policy."""
    __tablename__ = "studio_settings"
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text)
    updated: Mapped[float] = mapped_column(Float)
    updated_by: Mapped[Optional[str]] = mapped_column(Text)
