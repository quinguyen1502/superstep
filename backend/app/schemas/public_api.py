"""Models of the public workflow-trigger API (/api/hooks/*): the request body and the run payloads.

They document the routes in OpenAPI and in the public spec (docs/api/openapi.public.json) that the SDKs are generated
from. The payload itself is built by `services.trigger_service.run_result`; tests check that it validates against these.
"""
from typing import Any, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field
from .envelope import Envelope

RunStatus = Literal["queued", "running", "ok", "error", "cancelled", "timeout", "waiting", "expired"]


class StartRunRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"input": {"message": "where is my order A100"}, "mode": "async"}]})
    input: dict[str, Any] = Field(default_factory=dict, description="Initial state of the run.")
    mode: Literal["async", "sync"] = Field("async", description="`async` returns 202 at once. `sync` waits up to STUDIO_SYNC_WAIT_MAX seconds "
                                                                 "for the result, then falls back to 202 with `poll_url`.")
    callback_url: Optional[str] = Field(None, max_length=2000, description="Public http(s) URL that receives a signed POST when the run ends.")


class RunAccepted(BaseModel):
    """202 body: the run is queued; poll `poll_url` (also sent as the Location header)."""
    run_id: str = Field(..., examples=["3f9c2a1b7d"])
    status: RunStatus = Field(..., examples=["queued"])
    poll_url: str = Field(..., examples=["https://superstep.example.com/api/hooks/workflows/example/runs/3f9c2a1b7d"])


class RunMetrics(BaseModel):
    duration_ms: Optional[float] = None
    tokens_in: Optional[int] = None
    tokens_out: Optional[int] = None
    cost_usd: Optional[float] = None
    error_count: Optional[int] = None


class RunWaiting(BaseModel):
    """Set when status is `waiting`: the Human node the run is paused at, or the child run of a workflow tool it waits for."""
    node: Optional[str] = None
    prompt: Optional[str] = None
    child_run_id: Optional[str] = Field(None, description="Set while an Agent node's workflow tool runs: the child run the run waits for.")


class RunResult(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{
        "run_id": "3f9c2a1b7d", "workflow_id": "example", "status": "ok", "source": "api", "final_state": {"intent": "order_status"},
        "error": None, "waiting": None, "metrics": {"duration_ms": 412, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "error_count": 0},
        "trace_url": None, "started": 1761292800.0, "ended": 1761292800.4}]})
    run_id: str
    workflow_id: str
    status: RunStatus
    source: str = Field(..., description="Where the run came from: `api` for this API.")
    final_state: Optional[dict[str, Any]] = Field(None, description="State at the end; set once the run has finished.")
    error: Optional[Any] = Field(None, description="The last error event of a failed run (an object with `code` and `message`).")
    waiting: Optional[RunWaiting] = None
    parent_run_id: Optional[str] = Field(None, description="Set on the child run of a workflow tool: the run whose Agent node called it.")
    metrics: Optional[RunMetrics] = None
    trace_url: Optional[str] = None
    started: Optional[float] = Field(None, description="Unix time (seconds).")
    ended: Optional[float] = Field(None, description="Unix time (seconds); set once the run has finished.")


class RunPending(RunResult):
    """202 body of a `sync` run that is still going after STUDIO_SYNC_WAIT_MAX: the current result plus `poll_url`."""
    poll_url: str


class RunResultEnvelope(Envelope[RunResult]):
    """Success envelope carrying a run result."""


class RunAcceptedEnvelope(Envelope[Union[RunAccepted, RunPending]]):
    """Success envelope of a 202: a queued run, or a sync run that is still going."""
