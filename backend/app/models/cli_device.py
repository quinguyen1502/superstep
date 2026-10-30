from typing import Optional
from sqlalchemy import Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class CliDevice(Base):
    """One `superstep login` attempt (TASK-0167). Codes are stored as hashes. The token secret is kept only until the CLI polls once."""
    __tablename__ = "cli_devices"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    device_hash: Mapped[str] = mapped_column(Text, unique=True)
    user_code_hash: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[Optional[str]] = mapped_column(Text)
    user_id: Mapped[Optional[str]] = mapped_column(Text)
    token_id: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[str] = mapped_column(Text)  # pending, approved, denied
    secret: Mapped[Optional[str]] = mapped_column(Text)
    expires: Mapped[float] = mapped_column(Float)
    created: Mapped[float] = mapped_column(Float)
