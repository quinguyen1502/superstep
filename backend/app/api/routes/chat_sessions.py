"""Web chat (TASK-0084, REQ-0048): a workflow's Chat settings and its chat sessions. Messages and answers go over
the run socket (/ws/run with {chat_session_id, message} or {chat_session_id, resume_run_id, response}) so they stream.

GET  /api/workflows/{wid}/chat              the Chat settings (run right)       PUT the same (share right)
GET  /api/workflows/{wid}/chat/logo?v=      the chat's logo, published or not (run right, TASK-0145)
GET  /api/workflows/{wid}/chat/sessions     my chats                            POST a new chat
GET  /api/chat/sessions/{sid}?view=builder|visitor   turns with their steps     DELETE the chat
GET  /api/workflows/{wid}/chat/visitors     the published page's chats (run right, TASK-0141)
GET  /api/workflows/{wid}/chat/visitors/{sid}        one of them, read-only, with full steps
"""
from typing import Optional
from fastapi import APIRouter, Depends
from ...schemas.chat import ChatSettingsIn
from ..deps import chat_session_service, current_user
from .public_chat import logo_response

router = APIRouter(prefix="/api", tags=["chat"])


@router.get("/workflows/{wid}/chat")
def chat_settings(wid: str, user=Depends(current_user), svc=Depends(chat_session_service)): return svc.settings(wid, user["id"])

@router.put("/workflows/{wid}/chat")
def save_chat_settings(wid: str, body: ChatSettingsIn, user=Depends(current_user), svc=Depends(chat_session_service)):
    return svc.save_settings(wid, user["id"], body.model_dump(exclude_none=True))

@router.get("/workflows/{wid}/chat/logo")
def chat_logo(wid: str, v: Optional[str] = None, user=Depends(current_user), svc=Depends(chat_session_service)):
    return logo_response(svc.logo(wid, user["id"]), v is not None, "private")

@router.get("/workflows/{wid}/chat/sessions")
def list_chat_sessions(wid: str, user=Depends(current_user), svc=Depends(chat_session_service)): return svc.list(wid, user["id"])

@router.post("/workflows/{wid}/chat/sessions")
def create_chat_session(wid: str, user=Depends(current_user), svc=Depends(chat_session_service)): return svc.create(wid, user["id"])

@router.get("/chat/sessions/{sid}")
def get_chat_session(sid: str, view: str = "builder", user=Depends(current_user), svc=Depends(chat_session_service)):
    return svc.get(sid, user["id"], view)

@router.delete("/chat/sessions/{sid}")
def delete_chat_session(sid: str, user=Depends(current_user), svc=Depends(chat_session_service)): return svc.delete(sid, user["id"])

@router.get("/workflows/{wid}/chat/visitors")
def list_visitor_chats(wid: str, user=Depends(current_user), svc=Depends(chat_session_service)): return svc.visitors(wid, user["id"])

@router.get("/workflows/{wid}/chat/visitors/{sid}")
def get_visitor_chat(wid: str, sid: str, user=Depends(current_user), svc=Depends(chat_session_service)): return svc.visitor_session(wid, sid, user["id"])
