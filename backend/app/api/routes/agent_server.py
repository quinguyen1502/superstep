"""LangGraph Agent Server API, a subset, over Superstep workflows (docs/agent-server-api.md).

Base URL for LangGraph clients: `<studio>/api/lg`, e.g. `get_client(url="https://studio.example.com/api/lg", api_key="wft_…")`.
Bodies follow the Agent Server API (not the studio's `{success, data}` envelope), so the official clients work;
errors still use the error envelope with the usual HTTP status. Auth: `x-api-key` (what the SDK sends),
`X-Workflow-Token` or `Authorization: Bearer`, holding a workflow token (`wft_…`) or a user JWT.
"""
import asyncio, json
from typing import Any, Optional
from fastapi import APIRouter, Depends, Header, Request, Response
from fastapi.responses import JSONResponse, StreamingResponse
from ...schemas.agent_server import AssistantSearch, RunCreate, ThreadCreate, ThreadSearch
from ..deps import agent_server_service

router = APIRouter(prefix="/api/lg", tags=["agent-server"])


def principal(request: Request, x_api_key: Optional[str] = Header(None), x_workflow_token: Optional[str] = Header(None),
              authorization: Optional[str] = Header(None), svc=Depends(agent_server_service)):
    bearer = authorization[7:].strip() if authorization and authorization[:7].lower() == "bearer " else None
    return svc.principal((x_api_key or x_workflow_token or bearer or "").strip() or None)


def ok(data: Any, status: int = 200) -> JSONResponse:
    return JSONResponse(data, status_code=status)


@router.get("/info")
def info():
    return ok({"version": "superstep", "langgraph_py_version": None,
               "flags": {"assistants": True, "crons": False, "langsmith": False, "langsmith_tracing_replicas": False}})


@router.get("/ok")
def health():
    return ok({"ok": True})


# ---- assistants (one per workflow) ----
@router.post("/assistants/search")
def search_assistants(body: AssistantSearch, p=Depends(principal), svc=Depends(agent_server_service)):
    return ok(svc.search_assistants(p, body.graph_id, body.name, body.limit, body.offset))


@router.get("/assistants/{aid}")
def get_assistant(aid: str, p=Depends(principal), svc=Depends(agent_server_service)): return ok(svc.get_assistant(p, aid))


@router.get("/assistants/{aid}/graph")
def assistant_graph(aid: str, p=Depends(principal), svc=Depends(agent_server_service)): return ok(svc.graph(p, aid))


@router.get("/assistants/{aid}/schemas")
def assistant_schemas(aid: str, p=Depends(principal), svc=Depends(agent_server_service)): return ok(svc.schemas(p, aid))


# ---- threads ----
@router.post("/threads")
def create_thread(body: ThreadCreate, p=Depends(principal), svc=Depends(agent_server_service)):
    return ok(svc.create_thread(p, body.metadata, body.thread_id, body.if_exists))


@router.post("/threads/search")
def search_threads(body: ThreadSearch, p=Depends(principal), svc=Depends(agent_server_service)):
    return ok(svc.search_threads(p, body.metadata, body.status, body.limit, body.offset))


@router.get("/threads/{tid}")
def get_thread(tid: str, p=Depends(principal), svc=Depends(agent_server_service)): return ok(svc.get_thread(p, tid))


@router.delete("/threads/{tid}", status_code=204)
def delete_thread(tid: str, p=Depends(principal), svc=Depends(agent_server_service)):
    svc.delete_thread(p, tid); return Response(status_code=204)


@router.get("/threads/{tid}/state")
def thread_state(tid: str, p=Depends(principal), svc=Depends(agent_server_service)): return ok(svc.state(p, tid))


@router.post("/threads/{tid}/history")
def thread_history(tid: str, p=Depends(principal), svc=Depends(agent_server_service)): return ok([svc.state(p, tid)])


# ---- runs ----
async def _start(svc, p, tid: Optional[str], body: RunCreate):
    await svc.check_rate(p)
    return await asyncio.to_thread(svc.create_run, p, tid, body.assistant_id, body.input, body.command, body.metadata)


@router.post("/threads/{tid}/runs")
async def create_run(tid: str, body: RunCreate, p=Depends(principal), svc=Depends(agent_server_service)):
    run, _, _ = await _start(svc, p, tid, body); return ok(run)


@router.post("/runs")
async def create_stateless_run(body: RunCreate, p=Depends(principal), svc=Depends(agent_server_service)):
    run, _, _ = await _start(svc, p, None, body); return ok(run)


async def _wait(svc, p, tid: Optional[str], body: RunCreate):
    run, r, since = await _start(svc, p, tid, body)
    done = await svc.wait(p, run["thread_id"], r.id, since)
    return JSONResponse(svc.output(done), headers={"Content-Location": f"/api/lg/threads/{run['thread_id']}/runs/{r.id}"})


@router.post("/threads/{tid}/runs/wait")
async def wait_run(tid: str, body: RunCreate, p=Depends(principal), svc=Depends(agent_server_service)): return await _wait(svc, p, tid, body)


@router.post("/runs/wait")
async def wait_stateless_run(body: RunCreate, p=Depends(principal), svc=Depends(agent_server_service)): return await _wait(svc, p, None, body)


def _sse(event: str, data: Any) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n".encode()


async def _stream(svc, p, tid: Optional[str], body: RunCreate):
    run, r, since = await _start(svc, p, tid, body)
    modes = body.modes()

    async def events():
        async for ev, data in svc.stream(r, run["thread_id"], modes, since): yield _sse(ev, data)
    return StreamingResponse(events(), media_type="text/event-stream",
                             headers={"Content-Location": f"/api/lg/threads/{run['thread_id']}/runs/{r.id}", "Cache-Control": "no-store"})


@router.post("/threads/{tid}/runs/stream")
async def stream_run(tid: str, body: RunCreate, p=Depends(principal), svc=Depends(agent_server_service)): return await _stream(svc, p, tid, body)


@router.post("/runs/stream")
async def stream_stateless_run(body: RunCreate, p=Depends(principal), svc=Depends(agent_server_service)): return await _stream(svc, p, None, body)


@router.get("/threads/{tid}/runs")
def list_runs(tid: str, limit: int = 10, offset: int = 0, p=Depends(principal), svc=Depends(agent_server_service)):
    return ok(svc.list_runs(p, tid, limit, offset))


@router.get("/threads/{tid}/runs/{rid}")
def get_run(tid: str, rid: str, p=Depends(principal), svc=Depends(agent_server_service)): return ok(svc.get_run(p, tid, rid))


@router.get("/threads/{tid}/runs/{rid}/join")
async def join_run(tid: str, rid: str, p=Depends(principal), svc=Depends(agent_server_service)):
    await asyncio.to_thread(svc.get_run, p, tid, rid)
    return ok(svc.output(await svc.wait(p, tid, rid)))


@router.post("/threads/{tid}/runs/{rid}/cancel", status_code=204)
def cancel_run(tid: str, rid: str, p=Depends(principal), svc=Depends(agent_server_service)):
    svc.cancel(p, tid, rid); return Response(status_code=204)
