from typing import Optional
from sqlalchemy import Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Notification(Base):
    """In-app notification for one user, e.g. a run waiting for a human response."""
    __tablename__ = "notifications"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, index=True)
    kind: Mapped[str] = mapped_column(Text)             # run_waiting | run_expired
    run_id: Mapped[Optional[str]] = mapped_column(Text)
    workflow_id: Mapped[Optional[str]] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)            # English fallback; the UI renders by kind + params
    params: Mapped[Optional[str]] = mapped_column(Text)  # JSON {workflow_name, label, prompt}
    link: Mapped[Optional[str]] = mapped_column(Text)
    created: Mapped[float] = mapped_column(Float)
    read_at: Mapped[Optional[float]] = mapped_column(Float)
