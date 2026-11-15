"""Public workflow-trigger API: the routes external callers use, authenticated by a workflow token.

  POST   /api/hooks/workflows/{wid}/runs                      start a run (202 + poll_url / Location, or 200 in sync mode)
  GET    /api/hooks/workflows/{wid}/runs/{run_id}             status and result
  GET    /api/hooks/workflows/{wid}/schedules                 list schedules
  POST   /api/hooks/workflows/{wid}/schedules                 create a schedule
  POST   /api/hooks/workflows/{wid}/schedules/preview         next fire times of an expression
  PATCH  /api/hooks/workflows/{wid}/schedules/{sid}           update a schedule
  DELETE /api/hooks/workflows/{wid}/schedules/{sid}           delete a schedule

Tokens (`wft_…`) are managed by the workflow owner under /api/workflows/{wid}/tokens (`triggers.py`). These routes carry the
`public` tag: `api/openapi_public.py` builds the public spec (GET /openapi.public.json, docs/api/openapi.public.json) from them.
Schedules reuse `ScheduleService`. The token's owner is the schedule owner.
"""
import asyncio
from typing import Optional
from fastapi import APIRouter, Depends, Path, Request, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from ...core import config
from ...schemas.envelope import EnvelopeResponse, error_responses
from ...schemas.public_api import (RunAcceptedEnvelope, RunResultEnvelope, ScheduleDeletedEnvelope, ScheduleEnvelope,
                                   ScheduleListEnvelope, SchedulePreviewEnvelope, StartRunRequest)
from ...schemas.trigger import ScheduleIn, SchedulePatch, SchedulePreview
from ..deps import schedule_service, trigger_service

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
SID = Path(..., description="Schedule id returned when the schedule was created.", examples=["a1b2c3d4e5"])


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


def _owner(wid: str, token: Optional[str], triggers):
    return triggers.authenticate(wid, token).owner


@router.get("/workflows/{wid}/schedules", operation_id="listSchedules", summary="List schedules", response_model=None,
            responses={200: {"model": ScheduleListEnvelope, "description": "The workflow's schedules, soonest unchanged."},
                       **error_responses("TRIGGER_TOKEN_INVALID", "VALIDATION_ERROR")})
def list_schedules(wid: str = WID, token: Optional[str] = Depends(workflow_token), triggers=Depends(trigger_service),
                   schedules=Depends(schedule_service)):
    """Schedules of this workflow. A workflow token sees only its own workflow."""
    return schedules.list(wid, _owner(wid, token, triggers))


@router.post("/workflows/{wid}/schedules", operation_id="createSchedule", summary="Create a schedule", response_model=None,
             status_code=201,
             responses={201: {"model": ScheduleEnvelope, "description": "The schedule. The first fire is `next_runs[0]` when it is enabled."},
                        **error_responses("TRIGGER_TOKEN_INVALID", "SCHEDULE_CRON_INVALID", "SCHEDULE_LIMIT", "RUN_INPUT_INVALID",
                                          "RUN_INPUT_TOO_LARGE", "VALIDATION_ERROR")})
def create_schedule(body: ScheduleIn, wid: str = WID, token: Optional[str] = Depends(workflow_token),
                    triggers=Depends(trigger_service), schedules=Depends(schedule_service)):
    """Create a cron schedule. Each fire starts a run with `input` as the schedule's owner (the token owner).

    At most 20 schedules per workflow. A missed time fires once and is not replayed."""
    created = schedules.create(wid, _owner(wid, token, triggers), body.name, body.cron, body.timezone, body.input, body.enabled)
    return EnvelopeResponse(created, status_code=201)


@router.post("/workflows/{wid}/schedules/preview", operation_id="previewSchedule", summary="Preview a schedule",
             response_model=None,
             responses={200: {"model": SchedulePreviewEnvelope, "description": "The next fire times. Nothing is stored."},
                        **error_responses("TRIGGER_TOKEN_INVALID", "SCHEDULE_CRON_INVALID", "VALIDATION_ERROR")})
def preview_schedule(body: SchedulePreview, wid: str = WID, token: Optional[str] = Depends(workflow_token),
                     triggers=Depends(trigger_service), schedules=Depends(schedule_service)):
    """Next fire times of a cron expression in an IANA time zone. Requires a token for this workflow and stores nothing."""
    _owner(wid, token, triggers)
    return schedules.preview(body.cron, body.timezone)


@router.patch("/workflows/{wid}/schedules/{sid}", operation_id="updateSchedule", summary="Update a schedule",
              response_model=None,
              responses={200: {"model": ScheduleEnvelope, "description": "The schedule after the change."},
                         **error_responses("TRIGGER_TOKEN_INVALID", "SCHEDULE_NOT_FOUND", "SCHEDULE_CRON_INVALID",
                                           "RUN_INPUT_INVALID", "RUN_INPUT_TOO_LARGE", "VALIDATION_ERROR")})
def update_schedule(body: SchedulePatch, wid: str = WID, sid: str = SID, token: Optional[str] = Depends(workflow_token),
                    triggers=Depends(trigger_service), schedules=Depends(schedule_service)):
    """Change the fields you send. Omitted fields stay as they are. Turning a schedule on clears its off note."""
    return schedules.update(wid, sid, _owner(wid, token, triggers), **body.model_dump())


@router.delete("/workflows/{wid}/schedules/{sid}", operation_id="deleteSchedule", summary="Delete a schedule",
               response_model=None,
               responses={200: {"model": ScheduleDeletedEnvelope, "description": "The schedule is gone."},
                          **error_responses("TRIGGER_TOKEN_INVALID", "SCHEDULE_NOT_FOUND", "VALIDATION_ERROR")})
def delete_schedule(wid: str = WID, sid: str = SID, token: Optional[str] = Depends(workflow_token),
                    triggers=Depends(trigger_service), schedules=Depends(schedule_service)):
    """Delete one schedule of this workflow. Runs it already started are left in the history."""
    return schedules.delete(wid, sid, _owner(wid, token, triggers))
