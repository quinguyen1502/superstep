"""Public workflow-trigger API (TASK-0007): the only routes external callers use, authenticated by a workflow token.

  POST /api/hooks/workflows/{wid}/runs            start a run (202 + poll_url / Location, or 200 in sync mode)
  GET  /api/hooks/workflows/{wid}/runs/{run_id}   status and result

Tokens (`wft_…`) are managed by the workflow owner under /api/workflows/{wid}/tokens (`triggers.py`). These routes carry the
`public` tag: `api/openapi_public.py` builds the public spec (GET /openapi.public.json, docs/api/openapi.public.json) from them.
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Path, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from ...core import config
from ...schemas.envelope import EnvelopeResponse, error_responses
from ...schemas.public_api import RunAcceptedEnvelope, RunResultEnvelope, StartRunRequest
from ..deps import trigger_service

PUBLIC_TAG = "public"
router = APIRouter(prefix="/api/hooks", tags=[PUBLIC_TAG])

header_token = APIKeyHeader(name="X-Workflow-Token", scheme_name="WorkflowToken", auto_error=False,
                            description="Workflow token (`wft_…`), created by the workflow owner under **⋯ → API** in the editor.")
bearer_token = HTTPBearer(scheme_name="WorkflowBearer", bearerFormat="wft_…", auto_error=False,
                          description="The same workflow token as `Authorization: Bearer wft_…`.")


def workflow_token(x_workflow_token: Optional[str] = Security(header_token),
                   bearer: Optional[HTTPAuthorizationCredentials] = Security(bearer_token)) -> Optional[str]:
    """X-Workflow-Token wins over Authorization: Bearer."""
    if x_workflow_token: return x_workflow_token.strip()
    return bearer.credentials.strip() if bearer else None


WID = Path(..., description="Workflow id (shown in the editor URL and the API dialog).", examples=["example"])
RUN_ID = Path(..., description="Run id returned when the run was started.", examples=["3f9c2a1b7d"])


@router.post("/workflows/{wid}/runs", operation_id="startRun", summary="Start a run", response_model=None,
             status_code=202,
             responses={200: {"model": RunResultEnvelope, "description": "`sync` mode: the run finished within the wait."},
                        202: {"model": RunAcceptedEnvelope, "description": "Queued (`async`), or a `sync` run still going. "
                              "Poll `poll_url`; the same URL is in the `Location` header.",
                              "headers": {"Location": {"description": "The poll URL.", "schema": {"type": "string"}}}},
                        **error_responses("TRIGGER_TOKEN_INVALID", "RUN_INPUT_INVALID", "CALLBACK_URL_INVALID", "RUN_INPUT_TOO_LARGE",
                                          "VALIDATION_ERROR", "RATE_LIMITED")})
async def trigger_run(request: Request, body: StartRunRequest, wid: str = WID, token: Optional[str] = Depends(workflow_token),
                      svc=Depends(trigger_service)):
    """Queue a run of the workflow's latest saved version with `input` as the initial state.

    Each token may start `STUDIO_TRIGGER_RATE_LIMIT` runs per `STUDIO_TRIGGER_RATE_WINDOW` seconds; over the limit the
    answer is `429 RATE_LIMITED` with `Retry-After`."""
    tok = await asyncio.to_thread(svc.authenticate, wid, token)
    await svc.check_rate(tok)  # 429 RATE_LIMITED + Retry-After
    rid = await asyncio.to_thread(svc.start, tok, body.input, body.callback_url)
    poll = poll_url(request, wid, rid)
    if body.mode == "async":
        return EnvelopeResponse({"run_id": rid, "status": "queued", "poll_url": poll}, status_code=202, headers={"Location": poll})
    res = await svc.wait(tok, rid, min(config.sync_wait_max(), config.run_timeout() + 5))
    if res["status"] in ("queued", "running"):  # still going after STUDIO_SYNC_WAIT_MAX: poll instead of holding the connection
        return EnvelopeResponse({**res, "poll_url": poll}, status_code=202, headers={"Location": poll})
    return EnvelopeResponse(res, status_code=200)


def poll_url(request: Request, wid: str, rid: str) -> str:
    return str(request.url_for("run_status", wid=wid, run_id=rid))


@router.get("/workflows/{wid}/runs/{run_id}", operation_id="getRun", summary="Get a run", response_model=None,
            responses={200: {"model": RunResultEnvelope, "description": "Current status; `final_state` once finished."},
                       **error_responses("TRIGGER_TOKEN_INVALID", "RUN_NOT_FOUND", "VALIDATION_ERROR")})
def run_status(wid: str = WID, run_id: str = RUN_ID, token: Optional[str] = Depends(workflow_token), svc=Depends(trigger_service)):
    """Status and result of a run started with this workflow's tokens. Polling is not rate limited.

    Finished statuses: `ok`, `error`, `cancelled`, `timeout`, `waiting` (paused at a Human node), `expired`."""
    return svc.result(svc.authenticate(wid, token), run_id)
