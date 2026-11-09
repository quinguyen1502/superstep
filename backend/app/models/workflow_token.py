from typing import Optional
from sqlalchemy import Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class WorkflowToken(Base):
    """Per-workflow API trigger token. Only the SHA-256 of the secret is stored."""
    __tablename__ = "workflow_tokens"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    workflow_id: Mapped[str] = mapped_column(Text, index=True)
    owner: Mapped[str] = mapped_column(Text)
    name: Mapped[Optional[str]] = mapped_column(Text)
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    prefix: Mapped[Optional[str]] = mapped_column(Text)  # first characters, shown in the UI
    created: Mapped[Optional[float]] = mapped_column(Float)
    last_used: Mapped[Optional[float]] = mapped_column(Float)
    signing_secret: Mapped[Optional[str]] = mapped_column(Text)  # encrypted webhook HMAC secret
    signing_secret_prev: Mapped[Optional[str]] = mapped_column(Text)  # previous secret during rotation grace
    secret_rotated: Mapped[Optional[float]] = mapped_column(Float)    # when the secret was last rotated
    revoked: Mapped[Optional[float]] = mapped_column(Float)  # time of revocation; NULL = active
