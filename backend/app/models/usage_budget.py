from sqlalchemy import CheckConstraint, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class UsageBudget(Base):
    __tablename__ = "usage_budgets"
    __table_args__ = (
        CheckConstraint("(user_id IS NULL) <> (team_id IS NULL)", name="ck_usage_budget_target"),
        CheckConstraint("amount_cents > 0", name="ck_usage_budget_positive"),
    )

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), unique=True)
    team_id: Mapped[str | None] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), unique=True)
    amount_cents: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    created: Mapped[float] = mapped_column(Float)


class UsageBudgetWarning(Base):
    __tablename__ = "usage_budget_warnings"

    budget_id: Mapped[str] = mapped_column(ForeignKey("usage_budgets.id", ondelete="CASCADE"), primary_key=True)
    month: Mapped[str] = mapped_column(Text, primary_key=True)
    threshold: Mapped[int] = mapped_column(Integer, primary_key=True)
