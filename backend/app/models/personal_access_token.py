from typing import Optional
from sqlalchemy import Float, Index, Text, text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class PersonalAccessToken(Base):
    """A user's personal access token (TASK-0167). Only the SHA-256 of the secret is stored."""
    __tablename__ = "personal_access_tokens"
    __table_args__ = (Index("uq_personal_access_tokens_user_active_name", "user_id", "name", unique=True,  # TASK-0213
                            sqlite_where=text("revoked IS NULL"), postgresql_where=text("revoked IS NULL")),)
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, index=True)
    name: Mapped[str] = mapped_column(Text)
    token_hash: Mapped[str] = mapped_column(Text, unique=True)
    prefix: Mapped[str] = mapped_column(Text)
    created: Mapped[float] = mapped_column(Float)
    last_used: Mapped[Optional[float]] = mapped_column(Float)
    revoked: Mapped[Optional[float]] = mapped_column(Float)
