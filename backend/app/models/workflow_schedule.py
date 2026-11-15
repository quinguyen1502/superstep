from typing import Optional
from sqlalchemy import Boolean, Float, Text, true
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class WorkflowSchedule(Base):
    """A cron schedule that starts runs of a workflow as its creator."""
    __tablename__ = "workflow_schedules"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(Text, index=True)
    owner: Mapped[str] = mapped_column(Text, nullable=False)  # the runs belong to this user
    name: Mapped[str] = mapped_column(Text, nullable=False)
    cron: Mapped[str] = mapped_column(Text, nullable=False)
    timezone: Mapped[str] = mapped_column(Text, nullable=False)  # IANA, e.g. Asia/Ho_Chi_Minh
    input: Mapped[str] = mapped_column(Text, nullable=False)  # JSON object
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    next_run: Mapped[Optional[float]] = mapped_column(Float, index=True)  # NULL while disabled
    last_run: Mapped[Optional[float]] = mapped_column(Float)
    last_run_id: Mapped[Optional[str]] = mapped_column(Text)
    note: Mapped[Optional[str]] = mapped_column(Text)  # why the scheduler turned it off
    created: Mapped[float] = mapped_column(Float, nullable=False)
