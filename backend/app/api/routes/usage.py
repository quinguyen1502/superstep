"""Admin usage: run outcomes, tokens and estimated cost over a window, and product health counts (users.manage)."""
from typing import Literal, Optional
from fastapi import APIRouter, Depends
from ...schemas.usage import Bucket, UsageHealthEnvelope, UsageSummaryEnvelope, Window
from ...schemas.usage_budgets import BudgetAmount, BudgetCreate, BudgetListEnvelope
from ..deps import current_user, usage_budget_service, usage_service

router = APIRouter(prefix="/api/admin", tags=["usage"])


@router.get("/usage", response_model=None, responses={200: {"model": UsageSummaryEnvelope}})
def usage(window: Window = "7d", bucket: Optional[Bucket] = None, sort: Literal["runs", "cost"] = "runs",
          user=Depends(current_user), svc=Depends(usage_service)):
    """Totals, runs over time and the top 10 workflows, from the run records; cost counts priced runs only."""
    return svc.summary(user["id"], window, bucket, sort)


@router.get("/usage/health", response_model=None, responses={200: {"model": UsageHealthEnvelope}})
def usage_health(window: Window = "7d", user=Depends(current_user), svc=Depends(usage_service)):
    """Waiting and expired approvals, failed and retrying webhook deliveries, overdue and stopped schedules."""
    return svc.health(user["id"], window)


@router.get("/usage/budgets", response_model=None, responses={200: {"model": BudgetListEnvelope}})
def usage_budgets(user=Depends(current_user), svc=Depends(usage_budget_service)):
    return svc.list_budgets(user["id"])


@router.post("/usage/budgets", status_code=201)
def create_usage_budget(body: BudgetCreate, user=Depends(current_user), svc=Depends(usage_budget_service)):
    return svc.create(user["id"], body.scope, body.target_id, body.amount_usd)


@router.patch("/usage/budgets/{budget_id}")
def update_usage_budget(budget_id: str, body: BudgetAmount, user=Depends(current_user), svc=Depends(usage_budget_service)):
    return svc.update(user["id"], budget_id, body.amount_usd)


@router.delete("/usage/budgets/{budget_id}")
def delete_usage_budget(budget_id: str, user=Depends(current_user), svc=Depends(usage_budget_service)):
    return svc.delete(user["id"], budget_id)
