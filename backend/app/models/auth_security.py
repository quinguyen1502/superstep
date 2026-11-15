from typing import Optional
from sqlalchemy import Float, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class LoginThrottle(Base):
    """Failed sign-ins per e-mail. Unknown e-mails are counted too, so a lockout says nothing about who exists."""
    __tablename__ = "login_throttle"
    email: Mapped[str] = mapped_column(Text, primary_key=True)  # normalised
    failures: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_at: Mapped[float] = mapped_column(Float, nullable=False)  # start of the counting window
    locked_until: Mapped[Optional[float]] = mapped_column(Float)


class PasswordReset(Base):
    """A one-time password reset link. Only the SHA-256 of the token is stored."""
    __tablename__ = "password_resets"
    id: Mapped[str] = mapped_column(Text, primary_key=True)  # sha256(token) hex
    user_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    created: Mapped[float] = mapped_column(Float, nullable=False)
    expires: Mapped[float] = mapped_column(Float, nullable=False)
    used: Mapped[Optional[float]] = mapped_column(Float)
    created_by: Mapped[str] = mapped_column(Text, nullable=False)  # an admin's user id, or "self" for the e-mail flow
