"""Public demo mode (STUDIO_DEMO_MODE=true; docs/deploy/demo.md).

Design: "Try the demo" signs in with one public account, VISITOR_EMAIL (global role viewer). Each sign-in gets a fresh
anonymous visitor account of its own (start_visit: id VISITOR_PREFIX + random, viewer, the template's sample shares), so
run history, chats, waiting runs and notifications are per visitor, while the seeded samples stay shared and read-only;
visitors older than STUDIO_DEMO_VISITOR_TTL are removed with their runs and chats (purge_expired). RBAC already keeps
a viewer away from credentials, knowledge bases, API tokens, MCP servers, workflow creation and every admin page; demo mode
adds the rest:
- refuses(): the API refuses every write from the visitor except signing in/out, cancelling a run, answering a Human node,
  marking notifications read and starting or deleting their own chats in the Chat panel, so nobody can save, share or change the account (password, preferences, identities);
  sign-up and password reset are closed to everyone (DEMO_READ_ONLY).
- the visitor may run unsaved edits (run_service); the engine turns off Code, HTTP Tool and Send email nodes and runs LLM
  and Decision nodes on the offline mock model, so nothing leaves the server.
- check_run(): at most STUDIO_DEMO_RUN_RATE_LIMIT runs per client IP and minute.
- seed(): the visitor template and the sample workflows (shared with the visitor as viewer; chat turned on for the Chatbot) exist
  after every boot, since the free
  plan's SQLite file is wiped when the service sleeps.
The admin (STUDIO_ADMIN_EMAILS + STUDIO_ADMIN_PASSWORD) is a normal account and is not restricted."""
import re, secrets, time
from typing import Optional
from ..core import config, security
from ..core.errors import AppError
from ..core.logging import get_logger
from ..engine.examples import EXAMPLE
from ..engine.templates import BUILTINS
from ..models.database import Database
from ..models.workflow_share import WorkflowShare
from ..repositories import (ChatMessageRepository, ChatSessionRepository, ChatTriggerRepository, RunRepository, UserDataRepository, UserRepository,
                            WorkflowRepository, WorkflowShareRepository, WorkflowVersionRepository)
from .rate_limit import RateLimiter

log = get_logger("demo")
VISITOR_ID = "demo-visitor"  # the template account the public password belongs to; its sessions go to per-visitor accounts
VISITOR_PREFIX = "demo-v-"   # ids of the per-visitor accounts (start_visit)
VISITOR_EMAIL, VISITOR_PASSWORD = "demo@superstep.dev", "superstep-demo-2026"  # public on purpose: printed on the sign-in page
SAMPLES = ("builtin-chatbot", "builtin-router", "builtin-approval")  # the chat-enabled Chatbot first
CHAT_SAMPLE = "demo-chatbot"  # web chat on, so the Chat panel works for the visitor
_VISITOR_WRITES = re.compile(r"/api/(auth/(login|logout)|runs/[^/]+/cancel|notifications/(read-all|[^/]+/read)|approvals/inbox/[^/]+"
                             r"|workflows/[^/]+/chat/sessions|chat/sessions/[^/]+)")  # + their own chat sessions (Chat panel)
_CLOSED = re.compile(r"/api/auth/(register|password-reset(/confirm)?)")
UNSAFE = ("POST", "PUT", "PATCH", "DELETE")


def refuses(method: str, path: str, uid: Optional[str]) -> bool:
    """True when demo mode refuses this HTTP request (DEMO_READ_ONLY). Reads are always let through."""
    if method.upper() not in UNSAFE: return False
    if _CLOSED.fullmatch(path): return True
    return is_visitor(uid) and not _VISITOR_WRITES.fullmatch(path)


def is_visitor(uid: Optional[str]) -> bool:
    """The demo template account or one visitor's account."""
    return bool(uid) and (uid == VISITOR_ID or uid.startswith(VISITOR_PREFIX))


def options() -> dict:
    """What the sign-in page needs to offer "Try the demo"."""
    return {"email": VISITOR_EMAIL, "password": VISITOR_PASSWORD}


class DemoService:
    def __init__(self, limiter: Optional[RateLimiter] = None): self.limiter = limiter

    async def check_run(self, ip: str) -> None:
        limit = config.demo_run_rate_limit()
        if self.limiter is None or not limit: return
        ok, retry = await self.limiter.hit(f"demo-run:{ip}", limit, 60)
        if not ok: raise AppError("RATE_LIMITED", headers={"Retry-After": str(retry)}, retry_after=retry)


def seed(db: Database, owner: str) -> None:
    """Idempotent: the visitor account (viewer, the public password) and the samples owned by `owner` (an admin)."""
    from .workflow_service import WorkflowService
    from .chat_session_service import ChatSessionService
    users, wfs, shares = UserRepository(db), WorkflowRepository(db), WorkflowShareRepository(db)
    triggers = ChatTriggerRepository(db)
    chats = ChatSessionService(ChatSessionRepository(db), triggers, ChatMessageRepository(db), wfs, RunRepository(db))
    if users.get_by_id(VISITOR_ID) is None:
        users.add(VISITOR_ID, VISITOR_EMAIL, security.hash_password(VISITOR_PASSWORD), time.time())
    users.set_role(VISITOR_ID, "viewer"); users.set_active(VISITOR_ID, True)
    svc = WorkflowService(wfs, RunRepository(db), WorkflowVersionRepository(db))
    samples = [("example", dict(EXAMPLE))] + [(f"demo-{t['id'].removeprefix('builtin-')}", {**t["workflow"], "name": t["name"]})
                                             for sid in SAMPLES for t in BUILTINS if t["id"] == sid]
    for wid, wf in samples:
        if not wfs.exists(wid): svc.seed(owner, wid, wf)
        if wid == CHAT_SAMPLE and triggers.web(wid) is None: chats.save_settings(wid, owner, {"enabled": True})
        if shares.role_of(wid, VISITOR_ID) is None:
            shares.upsert(WorkflowShare(workflow_id=wid, user_id=VISITOR_ID, role="viewer", created=time.time(), shared_by=owner))
    purge_expired(db)
    log.info("Demo mode: %d sample workflows shared with %s", len(samples), VISITOR_EMAIL)


def start_visit(db: Database, now: Optional[float] = None) -> str:
    """A fresh anonymous visitor account (viewer, no password: only reachable through this session) with the template's
    sample shares, after removing expired visitors. Returns its id."""
    now = time.time() if now is None else now
    purge_expired(db, now)
    users, shares, wfs = UserRepository(db), WorkflowShareRepository(db), WorkflowRepository(db)
    vid = VISITOR_PREFIX + secrets.token_hex(8)
    users.add(vid, f"visitor-{vid.removeprefix(VISITOR_PREFIX)}@demo.superstep.dev", "", now)
    users.set_role(vid, "viewer")
    for wid, role in shares.for_user(VISITOR_ID).items():
        w = wfs.get(wid)
        if w is not None: shares.upsert(WorkflowShare(workflow_id=wid, user_id=vid, role=role, created=now, shared_by=w.owner))
    return vid


def purge_expired(db: Database, now: Optional[float] = None) -> int:
    """Remove visitors created more than STUDIO_DEMO_VISITOR_TTL ago, with their runs, chats, notifications and shares."""
    now = time.time() if now is None else now
    users, data, chats = UserRepository(db), UserDataRepository(db), ChatSessionRepository(db)
    gone = users.ids_created_before(VISITOR_PREFIX, now - config.demo_visitor_ttl())
    for vid in gone:
        fids = chats.feedback_ids_for_owner(vid)
        chats.delete_for_owner(vid); data.purge(vid, runs=True); data.delete_user(vid)
        try:
            from ..api.deps import get_job_queue
            from .chat_session_service import enqueue_feedback_deletes
            enqueue_feedback_deletes(get_job_queue(), fids)
        except Exception: log.warning("LangSmith feedback for visitor %s was not queued", vid)
    if gone: log.info("Demo mode: removed %d expired visitors", len(gone))
    return len(gone)
