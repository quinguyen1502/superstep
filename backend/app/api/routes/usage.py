"""Admin usage: run outcomes, tokens and estimated cost over a window, and product health counts (users.manage)."""
from typing import Literal, Optional
from fastapi import APIRouter, Depends
from ...schemas.usage import Bucket, UsageHealthEnvelope, UsageSummaryEnvelope, Window
from ..deps import current_user, usage_service

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
