from sqlalchemy import Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class NodeResult(Base):
    """Ledger of a finished side-effect node: its state update is reused instead of re-executing it."""
    __tablename__ = "node_results"
    run_id: Mapped[str] = mapped_column(Text, primary_key=True)
    node_id: Mapped[str] = mapped_column(Text, primary_key=True)
    iteration: Mapped[int] = mapped_column(Integer, primary_key=True)
    delta: Mapped[str] = mapped_column(Text)            # JSON state update returned by the node
    idempotency_key: Mapped[str] = mapped_column(Text)  # the key the node's side effects were sent with
    created: Mapped[float] = mapped_column(Float)
