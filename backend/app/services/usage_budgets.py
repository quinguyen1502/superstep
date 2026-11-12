import time
import uuid
from datetime import datetime
from decimal import Decimal

from ..core import config, permissions as P
from ..core.errors import AppError
from ..core.logging import get_logger
from ..models.usage_budget import UsageBudget

THRESHOLDS = (80, 100)
log = get_logger("usage.budgets")


def month_window(at: float) -> tuple[str, float, float, str]:
    zone = config.studio_timezone()
    month = datetime.fromtimestamp(at, zone).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    after = (month.replace(year=month.year + 1, month=1) if month.month == 12
             else month.replace(month=month.month + 1))
    return month.strftime("%Y-%m"), month.timestamp(), after.timestamp(), zone.key


class UsageBudgetService:
    def __init__(self, repo, access, audit, notifier):
        self.repo, self.access, self.audit, self.notifier = repo, access, audit, notifier

    @staticmethod
    def _target(budget: UsageBudget) -> tuple[str, str]:
        if budget.user_id is not None:
            return "user", budget.user_id
        assert budget.team_id is not None
        return "team", budget.team_id

    def list_budgets(self, actor: str) -> dict:
        self.access.require(actor, P.USERS_MANAGE)
        month, since, until, zone = month_window(time.time())
        budgets = self.repo.list_budgets()
        spend = self.repo.spend([b.id for b in budgets], since, until)
        targets = self.repo.targets()
        names = {(target["scope"], target["id"]): target["name"] for target in targets}
        rows = []
        for budget in budgets:
            scope, target_id = self._target(budget)
            cost, unpriced = spend.get(budget.id, (0.0, 0))
            rows.append({"id": budget.id, "scope": scope, "target_id": target_id,
                         "name": names.get((scope, target_id)) or self.repo.target(scope, target_id) or target_id,
                         "amount_usd": budget.amount_cents / 100, "spent_usd": cost, "unpriced_rows": unpriced})
        return {"month": month, "time_zone": zone, "budgets": rows, "targets": targets}

    def create(self, actor: str, scope: str, target_id: str, amount: Decimal) -> dict:
        self.access.require(actor, P.USERS_MANAGE)
        name = self.repo.target(scope, target_id)
        if name is None:
            raise AppError("NOT_FOUND")
        now = time.time()
        budget = UsageBudget(id=uuid.uuid4().hex, user_id=target_id if scope == "user" else None,
                             team_id=target_id if scope == "team" else None, amount_cents=int(amount * 100),
                             created_by=actor, created=now)
        if not self.repo.add(budget):
            raise AppError("USAGE_BUDGET_EXISTS")
        self._audit(actor, budget, "create", name)
        self._check_safely([budget], now)
        return {"id": budget.id}

    def update(self, actor: str, budget_id: str, amount: Decimal) -> dict:
        self.access.require(actor, P.USERS_MANAGE)
        budget = self.repo.update(budget_id, int(amount * 100))
        if budget is None:
            raise AppError("NOT_FOUND")
        self._audit(actor, budget, "update")
        self._check_safely([budget], time.time())
        return {"id": budget.id}

    def delete(self, actor: str, budget_id: str) -> dict:
        self.access.require(actor, P.USERS_MANAGE)
        budget = self.repo.delete(budget_id)
        if budget is None:
            raise AppError("NOT_FOUND")
        self._audit(actor, budget, "delete")
        return {"ok": True}

    def _audit(self, actor: str, budget: UsageBudget, action: str, name: str | None = None) -> None:
        scope, target_id = self._target(budget)
        self.audit.record(actor, f"policy.usage_budget_{action}", "usage_budget", budget.id,
                          name or self.repo.target(scope, target_id), scope=scope, budget_target_id=target_id,
                          amount_cents=budget.amount_cents)

    def check_owner(self, owner: str, at: float) -> None:
        try:
            self._check_safely(self.repo.list_budgets(owner), at)
        except Exception:
            log.exception("Could not load monthly usage budgets")

    def _check_safely(self, budgets: list[UsageBudget], at: float) -> None:
        if not budgets:
            return
        try:
            month, since, until, _ = month_window(at)
            spend = self.repo.spend([b.id for b in budgets], since, until)
        except Exception:
            log.exception("Could not calculate monthly budget spend")
            return
        for budget in budgets:
            try:
                self._check(budget, month, spend.get(budget.id, (0.0, 0))[0])
            except Exception:
                log.exception("Could not issue warning for usage budget %s", budget.id)

    def _check(self, budget: UsageBudget, month: str, spent: float) -> None:
        crossed = [t for t in THRESHOLDS if Decimal(str(spent)) * 10000 >= budget.amount_cents * t]
        if not crossed:
            return
        warned = self.repo.warned(budget.id, month)
        scope, target_id = self._target(budget)
        name = self.repo.target(scope, target_id)
        if name is None:
            return
        recipients = self.repo.recipients(budget)
        for threshold in crossed:
            if threshold in warned:
                continue
            deliveries = [self.notifier.budget_notice(uid, name, threshold, month) for uid in recipients]
            if self.repo.record_warning(budget, month, threshold, [notice for notice, prefs in deliveries if prefs["in_app"]]):
                for notice, prefs in deliveries:
                    self.notifier.deliver(notice, prefs)
