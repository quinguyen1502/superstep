from typing import Optional
from sqlalchemy import Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class AgentThread(Base):
    """A LangGraph Agent Server thread (`/api/lg`): a conversation of runs of one workflow. Its state is the state of
    its latest run. `token_id` is set when a workflow token created it (only that token sees it), else `owner` does."""
    __tablename__ = "agent_threads"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner: Mapped[str] = mapped_column(Text, index=True)
    token_id: Mapped[Optional[str]] = mapped_column(Text, index=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(Text)  # set by the first run
    meta: Mapped[Optional[str]] = mapped_column(Text)  # JSON object (LangGraph `metadata`)
    created: Mapped[float] = mapped_column(Float)
    updated: Mapped[float] = mapped_column(Float)


class AgentThreadRun(Base):
    """A Superstep run started on a thread (the run id is the Superstep run id)."""
    __tablename__ = "agent_thread_runs"
    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    thread_id: Mapped[str] = mapped_column(Text, index=True)
    meta: Mapped[Optional[str]] = mapped_column(Text)
    created: Mapped[float] = mapped_column(Float)
