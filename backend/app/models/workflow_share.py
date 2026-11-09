from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class WorkflowShare(Base):
    """A workflow shared with one user: role viewer (open, run) or editor (also edit)."""
    __tablename__ = "workflow_shares"
    workflow_id: Mapped[str] = mapped_column(Text, ForeignKey("workflows.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    role: Mapped[str] = mapped_column(Text)
    created: Mapped[float] = mapped_column(Float)
    shared_by: Mapped[str] = mapped_column(Text)
