"""Workflow tests (TASK-0067, TASK-0068, REQ-0042): test cases of a workflow and the suite runs that check them."""
from fastapi import APIRouter, Body, Depends
from ..deps import current_user, limit_body, workflow_test_service

router = APIRouter(prefix="/api/workflows/{wid}/tests", tags=["workflow tests"])


@router.get("")
def list_tests(wid: str, user=Depends(current_user), svc=Depends(workflow_test_service)): return svc.list(wid, user["id"])

@router.post("", dependencies=[Depends(limit_body)])
def create_test(wid: str, body=Body(None), user=Depends(current_user), svc=Depends(workflow_test_service)): return svc.create(wid, user["id"], body)

@router.put("/{tid}", dependencies=[Depends(limit_body)])
def update_test(wid: str, tid: str, body=Body(None), user=Depends(current_user), svc=Depends(workflow_test_service)): return svc.update(wid, tid, user["id"], body)

@router.delete("/{tid}")
def delete_test(wid: str, tid: str, user=Depends(current_user), svc=Depends(workflow_test_service)): return svc.delete(wid, tid, user["id"])

@router.post("/run")
def run_tests(wid: str, body=Body(None), user=Depends(current_user), svc=Depends(workflow_test_service)): return svc.run(wid, user["id"], body)

@router.get("/runs")
def suite_history(wid: str, user=Depends(current_user), svc=Depends(workflow_test_service)): return svc.history(wid, user["id"])

@router.get("/runs/{sid}")
def get_suite(wid: str, sid: str, user=Depends(current_user), svc=Depends(workflow_test_service)): return svc.suite(wid, sid, user["id"])

@router.post("/runs/{sid}/langsmith")
def send_suite(wid: str, sid: str, user=Depends(current_user), svc=Depends(workflow_test_service)): return svc.send_to_langsmith(wid, sid, user["id"])

@router.post("/runs/{sid}/cancel")
def cancel_suite(wid: str, sid: str, user=Depends(current_user), svc=Depends(workflow_test_service)): return svc.cancel(wid, sid, user["id"])

@router.post("/from-run/{rid}")
def draft_from_run(wid: str, rid: str, user=Depends(current_user), svc=Depends(workflow_test_service)): return svc.from_run(wid, rid, user["id"])
