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


class UsageModel(BaseModel):
    kind: Literal["llm", "embedding", "review"] = Field(..., description="Model calls of nodes, embeddings (knowledge bases), AI reviews of human steps.")
    model: str
    provider: str
    runs: int = Field(..., description="Runs that used this model (workflow tool child runs counted on their own).")
    calls: int
    errors: int = Field(..., description="Failed calls (an attempt answered by the fallback model counts here).")
    tokens_in: int
    tokens_out: int
    cost_usd: float = Field(..., description="Estimated cost of priced rows only.")
    unpriced_rows: int = Field(..., description="Rows whose model has no known price (cost unknown).")
    avg_duration_ms: Optional[float] = None


class UsageUser(BaseModel):
    user_id: Optional[str]
    email: Optional[str] = Field(None, description="Null when the user was deleted or anonymised.")
    deleted: bool
    runs: int
    tokens_in: int
    tokens_out: int
    cost_usd: float
    unpriced_runs: int


class UsageTeam(BaseModel):
    team_id: str
    name: Optional[str]
    members: int
    runs: int = Field(..., description="Top-level runs of the team's members; a member of several teams counts toward each.")
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
    models: list[UsageModel] = Field(..., description="By kind, model and provider, from runs that ended in the window.")
    models_since: Optional[float] = Field(None, description="When per-model data starts (the first stored row); null before any.")
    users: list[UsageUser] = Field(..., description="Top 20 users by the chosen sort.")
    teams: list[UsageTeam] = Field(..., description="Top 20 teams by the chosen sort.")
    teams_shared_members: int = Field(..., description="Users with runs in the window who are in more than one team.")


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


class ChannelRefusal(BaseModel):
    code: str
    kind: str = Field(..., description="Channel platform (slack, telegram, ...).")
    count: int


class ChannelHealth(BaseModel):
    refused: list[ChannelRefusal] = Field(..., description="Chat trigger messages refused in the window, by code and platform.")
    started: int = Field(..., description="Chat trigger messages that started a run in the window.")
    refused_total: int
    refusal_share: Optional[float] = Field(None, description="Refused over refused plus started; null without either.")


class UsageHealth(BaseModel):
    approvals: ApprovalHealth
    webhooks: WebhookHealth
    schedules: ScheduleHealth
    channels: ChannelHealth


UsageSummaryEnvelope = Envelope[UsageSummary]
UsageHealthEnvelope = Envelope[UsageHealth]
