"""REST run controls (TASK-0009, TASK-0006). Execution itself streams over /ws/run."""
from fastapi import APIRouter, Depends
from ..deps import current_user, run_service

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("/pending")
def pending_runs(user=Depends(current_user)):
    """Runs of the current user paused at a Human node (status `waiting`)."""
    return run_service().pending(user["id"])


@router.get("/{run_id}")
def run_detail(run_id: str, user=Depends(current_user)):
    """One run with its events, as the run history lists it (a workflow tool's child run in its parent's trace)."""
    return run_service().run_detail(run_id, user["id"])


@router.get("/{run_id}/checkpoints")
def run_checkpoints(run_id: str, user=Depends(current_user)):
    """Time travel: the checkpoints of a run (nodes that ran next and the state before them), then its final state."""
    return run_service().checkpoints(run_id, user["id"])


@router.post("/{run_id}/cancel")
def cancel_run(run_id: str, user=Depends(current_user)):
    """Stop a running run (on any API worker when Redis is configured) or close a waiting one."""
    run_service().cancel(run_id, user["id"])
    return {"run_id": run_id, "cancel_requested": True}
