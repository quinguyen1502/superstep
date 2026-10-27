from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import PlainTextResponse
from ...schemas.workflow import Rename, WorkflowIn
from ..deps import current_user, limit_body, run_service, workflow_service

router = APIRouter(prefix="/api", tags=["workflows"])

@router.get("/workflows")
def list_wf(all: bool = Query(False), user=Depends(current_user), svc=Depends(workflow_service)): return svc.list(user["id"], all)

@router.get("/workflows/{wid}")
def get_wf(wid: str, user=Depends(current_user), svc=Depends(workflow_service)): return svc.get(wid, user["id"])

@router.post("/workflows", dependencies=[Depends(limit_body)])
def save_wf(body: WorkflowIn, user=Depends(current_user), svc=Depends(workflow_service)): return svc.save(body.as_dict(), user["id"])

@router.patch("/workflows/{wid}")
def rename_wf(wid: str, body: Rename, user=Depends(current_user), svc=Depends(workflow_service)): return svc.rename(wid, body.name, user["id"])

@router.post("/workflows/{wid}/duplicate")
def dup_wf(wid: str, user=Depends(current_user), svc=Depends(workflow_service)): return svc.duplicate(wid, user["id"])

@router.delete("/workflows/{wid}")
def del_wf(wid: str, force: bool = Query(False), user=Depends(current_user), svc=Depends(workflow_service)): return svc.delete(wid, user["id"], force)

@router.get("/workflows/{wid}/runs")
def runs(wid: str, tests: bool = Query(False), user=Depends(current_user), svc=Depends(run_service)): return svc.history(wid, user["id"], tests)

@router.post("/validate", dependencies=[Depends(limit_body)])
def validate_wf(body: WorkflowIn, user=Depends(current_user), svc=Depends(workflow_service)): return svc.checked(body.as_dict(), user["id"])

# ---- versions (TASK-0008) ----
@router.get("/workflows/{wid}/versions")
def list_versions(wid: str, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0), user=Depends(current_user), svc=Depends(workflow_service)):
    return svc.list_versions(wid, user["id"], limit, offset)

@router.get("/workflows/{wid}/versions/diff")
def diff_versions(wid: str, a: int, b: int, user=Depends(current_user), svc=Depends(workflow_service)): return svc.diff_versions(wid, a, b, user["id"])

@router.get("/workflows/{wid}/versions/{n}")
def get_version(wid: str, n: int, user=Depends(current_user), svc=Depends(workflow_service)): return svc.get_version(wid, n, user["id"])

@router.post("/workflows/{wid}/versions/{n}/restore")
def restore_version(wid: str, n: int, user=Depends(current_user), svc=Depends(workflow_service)): return svc.restore_version(wid, n, user["id"])

# ---- export to code: Python (TASK-0070) and TypeScript / LangGraph.js (TASK-0082) ----
@router.get("/workflows/{wid}/python")
def python_code(wid: str, version: int | None = Query(None, ge=1), language: str = Query("python", max_length=40),
                user=Depends(current_user), svc=Depends(workflow_service)):
    return svc.export(wid, user["id"], version, language)

@router.get("/workflows/{wid}/code")
def workflow_code(wid: str, version: int | None = Query(None, ge=1), language: str = Query("python", max_length=40),
                  user=Depends(current_user), svc=Depends(workflow_service)):
    return svc.export(wid, user["id"], version, language)

@router.get("/workflows/{wid}/export/{language}/project")
def export_project(wid: str, language: str, version: int | None = Query(None, ge=1), user=Depends(current_user),
                   svc=Depends(workflow_service)):
    out = svc.export_project(wid, user["id"], version, language)
    return Response(out["content"], media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{out["filename"]}"'})

@router.get("/workflows/{wid}/export/{language}")
def export_file(wid: str, language: str, version: int | None = Query(None, ge=1), user=Depends(current_user),
                svc=Depends(workflow_service)):
    out = svc.export(wid, user["id"], version, language)
    return PlainTextResponse(out["code"], media_type=out["media_type"],
                             headers={"Content-Disposition": f'attachment; filename="{out["filename"]}"'})
