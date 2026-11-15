from sqlalchemy import and_, case, delete, func, select, union_all
from sqlalchemy.exc import IntegrityError

from ..models import Notification, Team, TeamMember, User
from ..models.database import Database
from ..models.run_usage import RunUsage
from ..models.usage_budget import UsageBudget, UsageBudgetWarning


def delete_budget_rows(session, condition) -> None:
    budget_ids = select(UsageBudget.id).where(condition)
    session.execute(delete(UsageBudgetWarning).where(UsageBudgetWarning.budget_id.in_(budget_ids)))
    session.execute(delete(UsageBudget).where(condition))


class UsageBudgetRepository:
    def __init__(self, db: Database):
        self.db = db

    def targets(self) -> list[dict]:
        with self.db.session() as s:
            users = s.execute(select(User.id, User.email).where(
                User.active.is_(True), User.email.is_not(None)).order_by(User.email)).all()
            teams = s.execute(select(Team.id, Team.name).order_by(Team.name)).all()
        return [{"scope": scope, "id": ident, "name": name}
                for scope, rows in (("user", users), ("team", teams)) for ident, name in rows]

    def target(self, scope: str, target_id: str) -> str | None:
        with self.db.session() as s:
            if scope == "team":
                return s.scalar(select(Team.name).where(Team.id == target_id))
            return s.scalar(select(User.email).where(User.id == target_id, User.active.is_(True)))

    def list_budgets(self, owner: str | None = None) -> list[UsageBudget]:
        q = select(UsageBudget).order_by(UsageBudget.created, UsageBudget.id)
        if owner is not None:
            teams = select(TeamMember.team_id).where(TeamMember.user_id == owner)
            q = q.where((UsageBudget.user_id == owner) | UsageBudget.team_id.in_(teams))
        with self.db.session() as s:
            return list(s.scalars(q))

    def add(self, budget: UsageBudget) -> bool:
        with self.db.session() as s:
            s.add(budget)
            try:
                s.commit()
            except IntegrityError:
                s.rollback()
                return False
        return True

    def update(self, budget_id: str, amount_cents: int) -> UsageBudget | None:
        with self.db.session() as s:
            budget = s.get(UsageBudget, budget_id, with_for_update=True)
            if budget is None:
                return None
            budget.amount_cents = amount_cents
            s.commit()
            return budget

    def delete(self, budget_id: str) -> UsageBudget | None:
        with self.db.session() as s:
            budget = s.get(UsageBudget, budget_id, with_for_update=True)
            if budget is None:
                return None
            delete_budget_rows(s, UsageBudget.id == budget_id)
            s.commit()
            return budget

    def spend(self, budget_ids: list[str], since: float, until: float) -> dict[str, tuple[float, int]]:
        if not budget_ids:
            return {}
        selected = UsageBudget.id.in_(budget_ids)
        owners = union_all(
            select(UsageBudget.id.label("budget_id"), UsageBudget.user_id.label("owner"))
            .where(selected, UsageBudget.user_id.is_not(None)),
            select(UsageBudget.id, TeamMember.user_id)
            .join(TeamMember, TeamMember.team_id == UsageBudget.team_id).where(selected),
        ).subquery()
        cost = func.coalesce(func.sum(RunUsage.cost_usd), 0.0)
        unpriced = func.sum(case((RunUsage.cost_usd.is_(None), 1), else_=0))
        q = (select(owners.c.budget_id, cost, unpriced)
             .join(RunUsage, and_(RunUsage.owner == owners.c.owner, RunUsage.created >= since, RunUsage.created < until))
             .group_by(owners.c.budget_id))
        with self.db.session() as s:
            return {bid: (round(float(total), 8), int(missing)) for bid, total, missing in s.execute(q)}

    def recipients(self, budget: UsageBudget) -> list[str]:
        q = select(User.id).where(User.active.is_(True))
        if budget.user_id is not None:
            q = q.where(User.id == budget.user_id)
        else:
            q = q.join(TeamMember, TeamMember.user_id == User.id).where(TeamMember.team_id == budget.team_id)
        with self.db.session() as s:
            return list(s.scalars(q))

    def warned(self, budget_id: str, month: str) -> set[int]:
        q = select(UsageBudgetWarning.threshold).where(
            UsageBudgetWarning.budget_id == budget_id, UsageBudgetWarning.month == month)
        with self.db.session() as s:
            return set(s.scalars(q))

    def record_warning(self, budget: UsageBudget, month: str, threshold: int, notices: list[Notification]) -> bool:
        """Commit the monthly claim and in-app notifications together."""
        with self.db.session() as s:
            current = s.get(UsageBudget, budget.id, with_for_update=True)
            if current is None or current.amount_cents != budget.amount_cents:
                return False
            s.add(UsageBudgetWarning(budget_id=budget.id, month=month, threshold=threshold))
            try:
                s.flush()
            except IntegrityError:
                s.rollback()
                return False
            s.add_all(notices)
            s.commit()
            return True
