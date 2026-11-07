"""Private bounded browser screenshots; separate from user-supplied chat attachments."""
from sqlalchemy import Float, ForeignKey, LargeBinary, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class BrowserArtifact(Base):
    __tablename__ = "browser_artifacts"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    owner: Mapped[str] = mapped_column(Text, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    principal_id: Mapped[str] = mapped_column(Text, nullable=False)
    run_id: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    connection_id: Mapped[str] = mapped_column(Text, nullable=False)
    group_id: Mapped[str] = mapped_column(Text, nullable=False)
    created: Mapped[float] = mapped_column(Float, nullable=False)
    expires: Mapped[float] = mapped_column(Float, nullable=False, index=True)
    data: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
