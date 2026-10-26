from typing import Optional
from sqlalchemy import Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Run(Base):
    __tablename__ = "runs"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_id: Mapped[Optional[str]] = mapped_column(Text)
    input: Mapped[Optional[str]] = mapped_column(Text)        # JSON
    events: Mapped[Optional[str]] = mapped_column(Text)       # JSON list
    final_state: Mapped[Optional[str]] = mapped_column(Text)  # JSON
    status: Mapped[Optional[str]] = mapped_column(Text)       # ok | error | cancelled | timeout | waiting | paused
    started: Mapped[Optional[float]] = mapped_column(Float)
    ended: Mapped[Optional[float]] = mapped_column(Float)
    # per-run summary metrics (TASK-0010); NULL for runs recorded before 0003
    duration_ms: Mapped[Optional[float]] = mapped_column(Float)
    tokens_in: Mapped[Optional[int]] = mapped_column(Integer)
    tokens_out: Mapped[Optional[int]] = mapped_column(Integer)
    cost_usd: Mapped[Optional[float]] = mapped_column(Float)  # NULL when a model has no known price
    error_count: Mapped[Optional[int]] = mapped_column(Integer)
    trace_id: Mapped[Optional[str]] = mapped_column(Text)     # OTel trace id (hex) when an exporter is configured
    trace_root: Mapped[Optional[str]] = mapped_column(Text)   # span id (hex) of the trace's root span: LangSmith's run id
    # human-in-the-loop (TASK-0006): owner of the run and the saved checkpoint while status == "waiting"
    owner: Mapped[Optional[str]] = mapped_column(Text, index=True)
    checkpoint: Mapped[Optional[str]] = mapped_column(Text)  # JSON {node, state, workflow}; cleared when the run ends
    source: Mapped[Optional[str]] = mapped_column(Text)  # ui | api (TASK-0007); NULL = ui (older runs)
    workflow_version: Mapped[Optional[int]] = mapped_column(Integer)  # version that ran; NULL = unsaved edits / older runs (TASK-0008)
    lease_gen: Mapped[int] = mapped_column(Integer, default=0, server_default="0")  # fencing token of the worker that owns it (TASK-0021)
    # API runs (TASK-0022 follow-up): the result callback survives a pause, so a resume from a chat channel delivers it too
    callback_url: Mapped[Optional[str]] = mapped_column(Text)
    code_runtime: Mapped[Optional[str]] = mapped_column(Text)  # where Code nodes ran: docker | subprocess; NULL = none (TASK-0056)
    callback_token_id: Mapped[Optional[str]] = mapped_column(Text)  # signs the callback (the token's secret)
    # JSON: the queued resume job of a waiting run, until the resumed segment records progress or a result (TASK-0127)
    resume_job: Mapped[Optional[str]] = mapped_column(Text)
