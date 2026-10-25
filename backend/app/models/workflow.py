from typing import Optional
from sqlalchemy import Boolean, Float, Text, false
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Workflow(Base):
    __tablename__ = "workflows"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(Text)
    data: Mapped[Optional[str]] = mapped_column(Text)  # workflow JSON (nodes, edges, state, source?)
    updated: Mapped[Optional[float]] = mapped_column(Float)
    owner: Mapped[Optional[str]] = mapped_column(Text)
    mcp_enabled: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())  # exposed as an MCP tool at /mcp (TASK-0114)
