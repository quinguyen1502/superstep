from typing import Optional
from sqlalchemy import Float, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column
from .base import Base


class Team(Base):
    """A named group of users; workflows can be shared with a team."""
    __tablename__ = "teams"
    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)
    description: Mapped[Optional[str]] = mapped_column(Text)
    created: Mapped[float] = mapped_column(Float)
    created_by: Mapped[str] = mapped_column(Text)


class TeamMember(Base):
    __tablename__ = "team_members"
    team_id: Mapped[str] = mapped_column(Text, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[str] = mapped_column(Text, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True, index=True)
    added: Mapped[float] = mapped_column(Float)


class WorkflowTeamShare(Base):
    """A workflow shared with every member of a team, as viewer or editor."""
    __tablename__ = "workflow_team_shares"
    workflow_id: Mapped[str] = mapped_column(Text, ForeignKey("workflows.id", ondelete="CASCADE"), primary_key=True)
    team_id: Mapped[str] = mapped_column(Text, ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True, index=True)
    role: Mapped[str] = mapped_column(Text)
    created: Mapped[float] = mapped_column(Float)
    shared_by: Mapped[str] = mapped_column(Text)
