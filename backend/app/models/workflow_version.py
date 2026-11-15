from typing import Optional
from sqlalchemy import Float, Integer, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class WorkflowVersion(Base):
    """Immutable snapshot written on every save that changes a workflow."""
    __tablename__ = "workflow_versions"
    __table_args__ = (UniqueConstraint("workflow_id", "version", name="uq_workflow_versions_wf_version"),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(Text, index=True)
    version: Mapped[int] = mapped_column(Integer)
    name: Mapped[Optional[str]] = mapped_column(Text)
    data: Mapped[str] = mapped_column(Text)          # workflow JSON, same shape as workflows.data
    author: Mapped[Optional[str]] = mapped_column(Text)  # user id
    created: Mapped[Optional[float]] = mapped_column(Float)
    note: Mapped[Optional[str]] = mapped_column(Text)    # e.g. "Restored from v2"
