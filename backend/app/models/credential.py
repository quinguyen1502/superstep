from typing import Optional
from sqlalchemy import Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Credential(Base):
    __tablename__ = "credentials"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner: Mapped[Optional[str]] = mapped_column(Text)
    name: Mapped[Optional[str]] = mapped_column(Text)
    provider: Mapped[Optional[str]] = mapped_column(Text)
    base_url: Mapped[Optional[str]] = mapped_column(Text)
    secret: Mapped[Optional[str]] = mapped_column(Text)  # Fernet token, never returned by the API
    headers: Mapped[Optional[str]] = mapped_column(Text)  # JSON {header: value}, non-secret
    settings: Mapped[Optional[str]] = mapped_column(Text)  # JSON, non-secret provider settings (SMTP host, port, ...; )
    hint: Mapped[Optional[str]] = mapped_column(Text)    # masked last 4 chars
    created: Mapped[Optional[float]] = mapped_column(Float)
