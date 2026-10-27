"""The published web chat (TASK-0140, REQ-0074, DEC-0067): /c/{slug} for visitors without the run right.

A chat is published when it is enabled and its `access` is "anonymous" (anyone with the link) or "signed_in" (any
account of this studio). Visitors read the page settings, list and read their own sessions, and start new ones; the
messages go over the public socket (TASK-0141). Every repository call acts for the trigger, never for the visitor, and
the answers never carry the workflow, its graph or its owner.

An anonymous visitor is a signed token `<id>.<hmac>` bound to the slug. The router keeps it in an HttpOnly cookie, or
the widget sends it in `X-Chat-Visitor` (decision 3); a bad or foreign token counts as none and a new one is issued.
"""
from __future__ import annotations
import hashlib, hmac, json, time, uuid
from dataclasses import dataclass
from typing import Optional
from ..core import config, security
from ..core.errors import AppError
from ..models import ChatSession, WorkflowChatTrigger
from ..repositories.chat_triggers import WEB
from .chat_session_service import DEFAULTS, PUBLIC, ChatSessionService

SIG_LEN = 32


@dataclass
class Visitor:
    """Who is chatting: a studio user (`owner`) for signed_in, else an anonymous visitor id; `token` when it is new."""
    owner: Optional[str] = None
    visitor: Optional[str] = None
    token: Optional[str] = None


class PublicChatService:
    def __init__(self, chat: ChatSessionService, limiter=None, secret: str = security.SECRET):
        self.chat, self.limiter, self.secret = chat, limiter, secret

    # ---- the published chat ----
    def published(self, slug: str) -> tuple[WorkflowChatTrigger, dict]:
        """The trigger and its settings, or CHAT_NOT_PUBLISHED (off, studio only, missing, or the public demo)."""
        t = self.chat.triggers.find(WEB, WEB, slug) if isinstance(slug, str) else None
        st = {**DEFAULTS, **json.loads(t.settings or "{}")} if t else {}
        if t is None or not t.enabled or st.get("access") not in PUBLIC or config.demo_mode() or self.chat.workflows.get(t.workflow_id) is None:
            raise AppError("CHAT_NOT_PUBLISHED")
        return t, st

    def page(self, slug: str, user: Optional[dict]) -> dict:
        t, st = self.published(slug)
        w = self.chat.workflows.get(t.workflow_id)
        return {"slug": slug, "title": st["title"] or w.name, "intro": st["intro"], "suggestions": st["suggestions"], "access": st["access"],
                "steps_mode": st["steps"], "signed_in": user is not None}

    def frame_ancestors(self, slug: str) -> str:
        """The page's `frame-ancestors` source list (decision 6): this studio and the allowed sites, or 'none'."""
        try: _, st = self.published(slug)
        except AppError: return "'none'"
        origins = st.get("embed_origins") or []
        return " ".join(["'self'", *origins]) if origins else "'none'"

    # ---- who is chatting ----
    def visitor(self, slug: str, st: dict, token: Optional[str], user: Optional[dict]) -> Visitor:
        if st["access"] == "signed_in":
            if user is None: raise AppError("CHAT_SIGN_IN_REQUIRED")
            return Visitor(owner=user["id"])
        vid = self.verify(slug, token)
        if vid: return Visitor(visitor=vid)
        vid = uuid.uuid4().hex[:16]
        return Visitor(visitor=vid, token=f"{vid}.{self._sig(slug, vid)}")

    def verify(self, slug: str, token: Optional[str]) -> Optional[str]:
        vid, _, sig = (token or "").partition(".")
        return vid if vid and len(sig) == SIG_LEN and hmac.compare_digest(sig, self._sig(slug, vid)) else None

    def _sig(self, slug: str, vid: str) -> str:
        return hmac.new(self.secret.encode(), f"chat-visitor:{slug}:{vid}".encode(), hashlib.sha256).hexdigest()[:SIG_LEN]

    async def check_read(self, ip: str) -> None:
        """The per-IP limit on page loads, session reads and new chats (decision 5)."""
        n = config.public_chat_rate_read()
        if not n or self.limiter is None: return
        ok, retry = await self.limiter.hit(f"pubchat-read:{ip}", n, config.public_chat_rate_window())
        if not ok: raise AppError("RATE_LIMITED", retry_after=retry)

    # ---- sessions ----
    def sessions(self, slug: str, token: Optional[str], user: Optional[dict]) -> tuple[list, Visitor]:
        t, st = self.published(slug); v = self.visitor(slug, st, token, user)
        rows = [] if v.token else self.chat.sessions.list_public(t.id, owner=v.owner, visitor=v.visitor)
        return [self.chat._session(s) for s in rows], v

    def create(self, slug: str, token: Optional[str], user: Optional[dict], embed: bool = False) -> tuple[dict, Visitor]:
        t, st = self.published(slug); v = self.visitor(slug, st, token, user); now = time.time()
        s = self.chat.sessions.add(ChatSession(id=uuid.uuid4().hex[:12], workflow_id=t.workflow_id, trigger_id=t.id, channel="embed" if embed else "web",
                                               owner=v.owner, visitor=v.visitor, title="", created=now, updated=now))
        return self.chat._session(s), v

    def get(self, slug: str, sid: str, token: Optional[str], user: Optional[dict]) -> tuple[dict, Visitor]:
        t, st = self.published(slug); v = self.visitor(slug, st, token, user)
        return self.chat.view(self.own(t, sid, v), st["steps"]), v

    def own(self, t: WorkflowChatTrigger, sid: str, v: Visitor) -> ChatSession:
        """The visitor's session of this chat, else CHAT_SESSION_NOT_FOUND (another visitor's, another chat's, a studio chat)."""
        s = self.chat.sessions.get(sid) if isinstance(sid, str) else None
        mine = s is not None and (s.owner == v.owner if v.owner else (s.visitor is not None and s.visitor == v.visitor and s.owner is None))
        if not mine or v.token or s.trigger_id != t.id or s.channel not in ("web", "embed"): raise AppError("CHAT_SESSION_NOT_FOUND")
        return s
