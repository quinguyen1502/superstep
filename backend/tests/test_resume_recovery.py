"""TASK-0127: an answer to a waiting run survives a restart of a server with the in-memory job queue. The answer is kept
on the run before its resume job is queued; start-up recovery queues it again when the job was lost, and first puts a
run that the resume had claimed, and that was cut off before it recorded anything, back to waiting."""
import asyncio, json
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_job_queue, run_service
from app.repositories import RunRepository
from app.services import job_queue as jq, run_worker as rw
from tests.test_inbox import H, user, waiting


@pytest.fixture(scope="module")
def c():
    with TestClient(app) as client: yield client


def answered_then_lost(c, monkeypatch):
    """An inbox answer whose resume job is lost with the queue (the server stopped before a worker took it)."""
    owner = user(c); _, rid = waiting(c, owner)
    with monkeypatch.context() as m:
        m.setattr(get_job_queue(), "enqueue", lambda job: None)
        assert c.post(f"/api/approvals/inbox/{rid}", json={"response": "approved"}, headers=H(owner["token"])).json()["success"]
    row = run_service().runs.get(rid)
    assert row.status == "waiting" and json.loads(row.resume_job)["response"] == "approved"
    return rid


def restart(monkeypatch, rid):
    """Start-up recovery in a new process (a fresh in-memory queue), limited to run `rid`: (worker, the jobs it queued)."""
    monkeypatch.setattr(rw, "_recovered", False)
    kept = RunRepository.list_resumes
    monkeypatch.setattr(RunRepository, "list_resumes", lambda self, limit=500: [r for r in kept(self, limit) if r.id == rid])
    monkeypatch.setattr(RunRepository, "list_unfinished", lambda self, limit=500: [])  # other tests' runs stay as they are
    q = jq.InMemoryJobQueue(); w = rw.RunWorker(q, run_service)
    asyncio.run(w.recover_unfinished())
    jobs = []
    while (job := q.dequeue(0.01)): jobs.append(job)
    return w, jobs


def test_an_answer_lost_with_the_queue_is_queued_again(c, monkeypatch):
    rid = answered_then_lost(c, monkeypatch)
    w, jobs = restart(monkeypatch, rid)
    assert [(j["kind"], j["run_id"], j["by"]["channel"]) for j in jobs] == [("resume", rid, "studio")]
    assert asyncio.run(w.run_job(jobs[0])) == "ok"
    row = run_service().runs.get(rid)
    assert json.loads(row.final_state)["decision"] == "approved" and row.resume_job is None  # used up


def test_a_resume_cut_off_before_it_recorded_anything_resumes_again(c, monkeypatch):
    rid = answered_then_lost(c, monkeypatch); svc = run_service()
    assert svc.runs.claim(rid, ("waiting",)) is not None  # a worker took the job, then the server stopped
    w, jobs = restart(monkeypatch, rid)
    assert svc.runs.get(rid).status == "waiting" and [j["run_id"] for j in jobs] == [rid]  # not started over from the beginning
    assert asyncio.run(w.run_job(jobs[0])) == "ok"
    assert json.loads(svc.runs.get(rid).final_state)["decision"] == "approved"


def test_a_resume_cut_off_too_often_ends_as_interrupted(c, monkeypatch):
    monkeypatch.setenv("STUDIO_RECOVER_MAX_ATTEMPTS", "1")
    rid = answered_then_lost(c, monkeypatch); svc = run_service()
    svc.runs.claim(rid, ("waiting",))
    _, jobs = restart(monkeypatch, rid)
    row = svc.runs.get(rid)
    assert jobs == [] and row.status == "error" and row.resume_job is None
    assert json.loads(row.events)[-1]["error"]["code"] == "RUN_INTERRUPTED"


def test_the_answer_is_kept_only_while_the_run_waits(c):
    svc = run_service(); owner = user(c); _, rid = waiting(c, owner)
    c.post(f"/api/approvals/inbox/{rid}", json={"response": "approved"}, headers=H(owner["token"]))  # the worker resumes it
    for _ in range(200):
        if svc.runs.get(rid).status == "ok": break
        asyncio.run(asyncio.sleep(0.05))
    assert svc.runs.get(rid).resume_job is None
    svc.runs.keep_resume({"kind": "resume", "run_id": rid, "owner": owner["id"], "response": "late"})
    assert svc.runs.get(rid).resume_job is None  # finished: nothing to keep
