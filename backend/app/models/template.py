from typing import Optional
from sqlalchemy import Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class WorkflowTemplate(Base):
    """A reusable starting point: a sanitised workflow graph, personal or org-wide. Built-ins live in code."""
    __tablename__ = "workflow_templates"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    scope: Mapped[str] = mapped_column(Text, nullable=False)  # user | org
    owner: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    data: Mapped[str] = mapped_column(Text, nullable=False)  # {"state", "nodes", "edges"}
    created: Mapped[float] = mapped_column(Float, nullable=False)
    updated: Mapped[float] = mapped_column(Float, nullable=False)
