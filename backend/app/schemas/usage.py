"""Models of the admin usage API (/api/admin/usage*): documentation in OpenAPI and a contract the tests validate."""
from typing import Literal, Optional
from pydantic import BaseModel, Field
from .envelope import Envelope

Window = Literal["24h", "7d", "30d"]
Bucket = Literal["hour", "day"]


class UsageTotals(BaseModel):
    runs: int = Field(..., description="Top-level runs started in the window (child runs of workflow tools are part of their parent).")
    by_status: dict[str, int]
    success_rate: Optional[float] = Field(None, description="ok over finished runs (ok, error, timeout, cancelled); null without finished runs.")
    tokens_in: int
    tokens_out: int
    cost_usd: float = Field(..., description="Estimated cost of priced runs only.")
    unpriced_runs: int = Field(..., description="Finished runs whose model has no known price (cost unknown).")
    unpriced_share: Optional[float] = None


class UsageBucket(BaseModel):
    start: float = Field(..., description="Bucket start, Unix seconds.")
    ok: int
    error: int
    timeout: int
    cancelled: int
    other: int = Field(..., description="Runs still queued, running or waiting.")


class UsageWorkflow(BaseModel):
    workflow_id: Optional[str]
    name: Optional[str] = Field(None, description="Null when the workflow was deleted.")
    runs: int
    errors: int
    error_rate: Optional[float]
    tokens_in: int
    tokens_out: int
    cost_usd: float
    unpriced_runs: int


class UsageSummary(BaseModel):
    window: Window
    bucket: Bucket
    bucket_seconds: int
    since: float
    until: float
    totals: UsageTotals
    series: list[UsageBucket]
    top_workflows: list[UsageWorkflow]
    grafana_url: Optional[str] = Field(None, description="STUDIO_GRAFANA_URL when set.")


class ApprovalHealth(BaseModel):
    waiting: int
    oldest_age_s: Optional[float]
    expired: int


class WebhookHealth(BaseModel):
    failed: int
    retrying: int


class DisabledSchedule(BaseModel):
    id: str
    workflow_id: str
    name: str
    note: Optional[str]


class ScheduleHealth(BaseModel):
    overdue: int
    disabled: int
    disabled_list: list[DisabledSchedule]


class UsageHealth(BaseModel):
    approvals: ApprovalHealth
    webhooks: WebhookHealth
    schedules: ScheduleHealth


UsageSummaryEnvelope = Envelope[UsageSummary]
UsageHealthEnvelope = Envelope[UsageHealth]
