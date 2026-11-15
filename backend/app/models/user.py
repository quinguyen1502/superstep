from typing import Optional
from sqlalchemy import Boolean, Float, Text, true
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class User(Base):
    __tablename__ = "users"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(Text, unique=True)
    password: Mapped[Optional[str]] = mapped_column(Text)  # "pbkdf2_sha256$iter$salt$hash"
    created: Mapped[Optional[float]] = mapped_column(Float)
    # notification preferences
    notify_in_app: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    notify_email: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    lang: Mapped[Optional[str]] = mapped_column(Text)  # en | vi: chat messages (approval requests, codes); NULL = en
    # RBAC: global role (core.permissions.ROLES) and whether the account may sign in
    role: Mapped[str] = mapped_column(Text, default="editor", server_default="editor")
    active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    # when the password last changed; tokens issued before it no longer work
    password_changed: Mapped[Optional[float]] = mapped_column(Float)

    @property
    def is_admin(self) -> bool:  # replaces the users.is_admin column (migration 0021)
        return self.role == "admin"
