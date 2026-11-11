from typing import Optional
from sqlalchemy import Float, Index, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class RunUsage(Base):
    """Model usage of one finished run, one row per node, kind, model and provider (written once at run end).
    Deleted with its run; the admin Usage page aggregates it in SQL."""
    __tablename__ = "run_usage"
    __table_args__ = (UniqueConstraint("run_id", "node_id", "kind", "model", "provider", name="uq_run_usage_key"),
                      Index("ix_run_usage_created", "created"), Index("ix_run_usage_owner_created", "owner", "created"))
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    workflow_id: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[Optional[str]] = mapped_column(Text)
    node_id: Mapped[str] = mapped_column(Text, nullable=False)
    kind: Mapped[str] = mapped_column(Text, nullable=False)  # llm | embedding | review
    model: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_in: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float)  # NULL when the model has no price
    calls: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    errors: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    duration_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created: Mapped[float] = mapped_column(Float, nullable=False)  # the run's end
