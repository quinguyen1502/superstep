"""Web chat (TASK-0084, REQ-0048): a workflow's Chat settings and its chat sessions. Messages and answers go over
the run socket (/ws/run with {chat_session_id, message} or {chat_session_id, resume_run_id, response}) so they stream.

GET  /api/workflows/{wid}/chat              the Chat settings (run right)       PUT the same (share right)
GET  /api/workflows/{wid}/chat/logo?v=      the chat's logo, published or not (run right, TASK-0145)
GET  /api/workflows/{wid}/chat/sessions     my chats                            POST a new chat
GET  /api/chat/sessions/{sid}?view=builder|visitor   turns with their steps     DELETE the chat
GET  /api/workflows/{wid}/chat/visitors     the published page's chats (run right, TASK-0141); ?thumbs_down=1 filters
GET  /api/workflows/{wid}/chat/visitors/{sid}        one of them, read-only, with full steps
GET  /api/workflows/{wid}/chat/ratings      up and down over 7 and 30 days (TASK-0162)
PUT  /api/chat/sessions/{sid}/turns/{tid}/rating     the session owner's thumb, and an optional comment on down
DELETE /api/chat/sessions/{sid}/turns/{tid}/rating
"""
from typing import Optional
from fastapi import APIRouter, Depends
from ...schemas.chat import ChatRatingIn, ChatSettingsIn
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
def list_visitor_chats(wid: str, thumbs_down: bool = False, user=Depends(current_user), svc=Depends(chat_session_service)):
    return svc.visitors(wid, user["id"], thumbs_down)

@router.get("/workflows/{wid}/chat/ratings")
def chat_ratings(wid: str, user=Depends(current_user), svc=Depends(chat_session_service)): return svc.rating_totals(wid, user["id"])

@router.put("/chat/sessions/{sid}/turns/{tid}/rating")
def rate_turn(sid: str, tid: str, body: ChatRatingIn, user=Depends(current_user), svc=Depends(chat_session_service)):
    return svc.rate_owned(sid, tid, user["id"], body.value, body.comment)

@router.delete("/chat/sessions/{sid}/turns/{tid}/rating")
def unrate_turn(sid: str, tid: str, user=Depends(current_user), svc=Depends(chat_session_service)):
    return svc.unrate_owned(sid, tid, user["id"])

@router.get("/workflows/{wid}/chat/visitors/{sid}")
def get_visitor_chat(wid: str, sid: str, user=Depends(current_user), svc=Depends(chat_session_service)): return svc.visitor_session(wid, sid, user["id"])
