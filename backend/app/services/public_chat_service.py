"""The published web chat (TASK-0140, REQ-0074, DEC-0067): /c/{slug} for visitors without the run right.

A chat is published when it is enabled and its `access` is "anonymous" (anyone with the link) or "signed_in" (any
account of this studio). Visitors read the page settings, list and read their own sessions, and start new ones; the
messages go over the public socket (TASK-0141). Every repository call acts for the trigger, never for the visitor, and
the answers never carry the workflow, its graph or its owner.

Messages and answers go over the public socket (TASK-0141, decision 4): `plan_message` checks the visitor, the limits
and the session, then plans a `source = "chat"` run as the workflow's owner (DEC-0023) through RunService.plan; the
socket forwards only `public_event`s, cut down to the page's steps mode.

An anonymous visitor is a signed token `<id>.<hmac>` bound to the slug. The router keeps it in an HttpOnly cookie, or
the widget sends it in `X-Chat-Visitor` (decision 3); a bad or foreign token counts as none and a new one is issued.
"""
from __future__ import annotations
import asyncio, hashlib, hmac, json, time, uuid
from dataclasses import dataclass
from typing import Callable, Optional
from ..core import config, security
from ..core.errors import AppError
from ..models import ChatSession, WorkflowChatTrigger
from ..repositories.chat_triggers import WEB
from ..engine import agents
from .chat_session_service import DEFAULTS, PUBLIC, ChatSessionService
from .chat_attachment_service import DEFAULTS as ATTACH_DEFAULTS

SIG_LEN = 32
DAY = 86400
HIDDEN = ("start", "end", "agent", "agent_exit")  # as steps_of: an Agent shows its tool calls (and model calls in full)
LABEL_KEYS = ("type", "node", "label", "node_type", "iteration", "ts")
FULL_KEYS = ("duration_ms", "input", "delta", "errors", "code", "agent")
QUESTION_KEYS = ("prompt", "options", "choices", "fields", "kind", "input_type", "placeholder")


def public_event(ev: dict, mode: str, reply_field: str) -> Optional[dict]:
    """What the page may see of a run event (decision 4), or None: the reply's tokens, the steps in `mode`, the visitor's
    question, the final status and errors. Never the state, node input or output below `full`, metrics or trace links."""
    t, node_type = ev.get("type"), ev.get("node_type")
    if t == "run_started": return {"type": t, "run_id": ev.get("run_id"), "ts": ev.get("ts")}
    if t == "run_summary": return {"type": t, "run_id": ev.get("run_id"), "status": ev.get("status"), "ts": ev.get("ts")}
    if t == "node_token":
        return {k: ev.get(k) for k in ("type", "node", "iteration", "field", "delta", "ts")} if ev.get("field") == reply_field else None
    if t == "run_waiting":
        return {k: ev[k] for k in LABEL_KEYS + QUESTION_KEYS if k in ev}
    if t == "error" and not ev.get("node"): return {k: ev[k] for k in ("type", "error", "errors", "issues", "ts") if k in ev}
    if t in ("node_started", "node_finished", "error"):
        if mode == "none" or node_type in HIDDEN or (node_type == "agent_model" and mode != "full"): return None
        out = {k: ev[k] for k in LABEL_KEYS if k in ev}
        if t == "error": out["status"] = "error"
        if mode == "full":
            out.update({k: ev[k] for k in FULL_KEYS if k in ev})
            if isinstance(out.get("input"), dict): out["input"] = agents.visible(out["input"])
        return out
    if t in ("run_cancelled", "run_timeout"): return {"type": t, "ts": ev.get("ts")}
    return None


@dataclass
class Visitor:
    """Who is chatting: a studio user (`owner`) for signed_in, else an anonymous visitor id; `token` when it is new."""
    owner: Optional[str] = None
    visitor: Optional[str] = None
    token: Optional[str] = None


class PublicChatService:
    def __init__(self, chat: ChatSessionService, limiter=None, counter=None, secret: str = security.SECRET):
        self.chat, self.limiter, self.counter, self.secret = chat, limiter, counter, secret

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
                "steps_mode": st["steps"], "signed_in": user is not None, "embed_origins": st["embed_origins"], "logo": st["logo"],  # the widget's iframe checks its host
                "attachments": self.attachment_limits(st)}

    @staticmethod
    def attachment_limits(st: dict) -> dict:
        """What the page's composer checks before an upload (TASK-0177): on or off, kinds, count and size; never the field."""
        a = {**ATTACH_DEFAULTS, **(st.get("attachments") or {})}
        return {k: a[k] for k in ("enabled", "kinds", "max_files", "max_mb")}

    def logo(self, slug: str):
        t, _ = self.published(slug)
        logo = self.chat.triggers.logo(t.id)
        if logo is None: raise AppError("CHAT_LOGO_NOT_FOUND")
        return logo

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

    def turns(self, slug: str, sid: str, after: Optional[str], token: Optional[str], user: Optional[dict]) -> tuple[dict, Visitor]:
        """The chat's turns after the turn `after` (incremental history, TASK-0215); all of them when `after` is empty."""
        view, v = self.get(slug, sid, token, user)
        rows = view["turns"]
        if after:
            at = next((i for i, x in enumerate(rows) if x["id"] == after), None)
            if at is None: raise AppError("CHAT_TURN_NOT_FOUND")
            rows = rows[at + 1:]
        return {"turns": rows}, v

    def rate(self, slug: str, sid: str, tid: str, token: Optional[str], user: Optional[dict], value, comment) -> tuple[dict, Visitor]:
        """The visitor rates one of their own finished answers. An unpublished chat refuses it (DEC-0070)."""
        t, st = self.published(slug); v = self.visitor(slug, st, token, user)
        return self.chat.rate(self.own(t, sid, v), tid, value, comment), v

    def unrate(self, slug: str, sid: str, tid: str, token: Optional[str], user: Optional[dict]) -> tuple[dict, Visitor]:
        t, st = self.published(slug); v = self.visitor(slug, st, token, user)
        return self.chat.unrate(self.own(t, sid, v), tid), v

    def own(self, t: WorkflowChatTrigger, sid: str, v: Visitor) -> ChatSession:
        """The visitor's session of this chat, else CHAT_SESSION_NOT_FOUND (another visitor's, another chat's, a studio chat)."""
        s = self.chat.sessions.get(sid) if isinstance(sid, str) else None
        mine = s is not None and (s.owner == v.owner if v.owner else (s.visitor is not None and s.visitor == v.visitor and s.owner is None))
        if not mine or v.token or s.trigger_id != t.id or s.channel not in ("web", "embed"): raise AppError("CHAT_SESSION_NOT_FOUND")
        return s

    # ---- a message or an answer (the public socket) ----
    async def plan_message(self, slug: str, token: Optional[str], user: Optional[dict], req, ip: str, plan: Callable):
        """(RunPlan, owner, steps mode, reply field) for `{chat_session_id, message}` or `{chat_session_id, response, node?}`.
        `plan` is RunService.plan; the run is the owner's and the session's, nothing else can be asked for.
        `node` is the question on the page. Another slot of the same wave is not accepted."""
        if not isinstance(req, dict) or set(req) - {"chat_session_id", "message", "response", "resume_run_id", "locale", "node", "attachment_ids"}:
            raise AppError("RUN_REQUEST_INVALID")
        t, st = self.published(slug); v = self.visitor(slug, st, token, user)
        s = self.own(t, req.get("chat_session_id"), v)
        w = self.chat.workflows.get(t.workflow_id); owner = w.owner or t.owner
        answering = "response" in req
        await self.check_message(t, st, v, ip, daily=not answering)
        if answering and req.get("attachment_ids"): raise AppError("RUN_REQUEST_INVALID")  # a Human node's answer is text only
        if answering:
            turns = self.chat.sessions.turns(s.id); last = turns[-1] if turns else None
            if last is None or last.role != "assistant" or last.status != "waiting" or not last.run_id: raise AppError("RUN_NOT_WAITING")
            if last.answered_by == "reviewer": raise AppError("CHAT_ANSWER_BY_REVIEWER")
            if req.get("resume_run_id") not in (None, last.run_id): raise AppError("RUN_NOT_WAITING")
            shown = last.node if isinstance(last.node, str) and last.node else None
            node = req.get("node") if isinstance(req.get("node"), str) and req.get("node") else None
            if node and shown and node != shown: raise AppError("RUN_NOT_WAITING")
            body = {"resume_run_id": last.run_id, "response": req.get("response")}
            if node or shown: body["node"] = node or shown
            p = await asyncio.to_thread(plan, owner, body)
            self.chat.record_answer(s.id, last.run_id, req.get("response"))
        else:
            prep = self.chat.prepare(s, t, req.get("message"), req.get("attachment_ids"))
            p = await asyncio.to_thread(plan, owner, {"workflow_id": t.workflow_id, "input": prep["input"]})
            p.run_id, p.source = uuid.uuid4().hex[:10], "chat"
            self.chat.write(s, t, prep["text"], p.run_id, v.owner or "visitor", prep["attachment_ids"])
        return p, owner, st["steps"], t.reply_field

    async def check_message(self, t: WorkflowChatTrigger, st: dict, v: Visitor, ip: str, daily: bool = True) -> None:
        """Per visitor and per IP in a window, then the chat's daily cap (decision 5); nothing runs when one says no."""
        win = config.public_chat_rate_window()
        for key, n in ((f"pubchat-v:{t.id}:{v.owner or v.visitor}", config.public_chat_rate_visitor()), (f"pubchat-ip:{ip}", config.public_chat_rate_ip())):
            if n and self.limiter is not None:
                ok, retry = await self.limiter.hit(key, n, win)
                if not ok: raise AppError("RATE_LIMITED", retry_after=retry)
        cap = int(st.get("daily_limit") or 0)
        if daily and cap and self.counter is not None:
            day = int(time.time() // DAY)
            count, _ = await asyncio.to_thread(self.counter.add, f"pubchat-day:{t.id}:{day}", 1, DAY)
            if count > cap: raise AppError("CHAT_DAILY_LIMIT")
