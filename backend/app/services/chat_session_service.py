"""Web chat (TASK-0084, REQ-0048, DEC-0052..0054): a workflow answers a conversation, one run per message.

A workflow's chat is a chat trigger of kind "web" (channel_id = place = "web"); its settings live in the trigger's
`settings` JSON. Each message starts a `source="chat"` run (over the studio's run socket, so it streams) with
{input_field: text, messages_field: the last `max_turns` exchanges + this message}. When the run settles,
ChatRunService.on_settled (reply-once per settled state, as for Slack/Telegram) hands it to answer(), which writes the
assistant turn: the reply field, the Human node's question, or the error.

Phase 1 is the studio: signed-in users with the run right. Phase 2 (REQ-0074, DEC-0067) publishes the chat at
/c/{slug} with `access` "anonymous" or "signed_in" (services/public_chat_service.py); its sessions have `channel`
"web" or "embed". Attachments are reserved.
"""
from __future__ import annotations
import base64, binascii, hashlib, json, re, time, uuid
from urllib.parse import urlparse
from typing import Optional
from ..core import permissions as P
from ..core.errors import AppError
from ..engine import agents
from ..engine.limits import size
from ..core import config
from ..models import ChatMessage, ChatRating, ChatSession, ChatTurn, Run, WorkflowChatTrigger
from ..repositories import ChatMessageRepository, ChatSessionRepository, ChatTriggerRepository, RunRepository, WorkflowRepository
from ..repositories.chat_triggers import WEB

ACCESS = ("studio", "anonymous", "signed_in")  # anonymous / signed_in publish the chat at /c/{slug} (DEC-0067)
PUBLIC = ("anonymous", "signed_in")
STEPS = ("none", "labels", "full")
ANSWERED_BY = ("visitor", "reviewer")
DEFAULTS = {"access": "studio", "messages_field": "", "max_turns": 10, "steps": "labels", "retention_days": 30,
            "title": "", "intro": "", "suggestions": [], "daily_limit": 500, "embed_origins": [], "logo": ""}
MAX_TURNS, RETENTION_MAX, TEXT_MAX, TITLE_MAX = 50, 3650, 4000, 60
COMMENT_MAX = 1000
RATEABLE = ("ok", "error")  # a waiting question, and a cancelled run, are not an answer to rate (DEC-0070)
INTRO_MAX, SUGGESTIONS_MAX, SUGGESTION_MAX, DAILY_MAX, ORIGINS_MAX = 1000, 4, 120, 100_000, 10
LOGO_MAX = 256 * 1024
LOGO_TYPES = ((b"\x89PNG\r\n\x1a\n", "image/png"), (b"\xff\xd8\xff", "image/jpeg"))  # WebP: RIFF....WEBP (logo_of)
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]{1,62}[a-z0-9]$")
RESERVED_SLUGS = frozenset({"api", "ws", "new", "admin", "login", "embed", "widget", "static", "assets"})


def origin_of(value) -> Optional[str]:
    """An embed origin as `scheme://host[:port]` (https, or http on localhost), lower-cased; None when it is not one."""
    if not isinstance(value, str): return None
    u = urlparse(value.strip().rstrip("/").lower())
    try: port = u.port
    except ValueError: return None
    local = u.hostname in ("localhost", "127.0.0.1")
    if not u.hostname or u.path or u.query or u.fragment or u.username or u.password or not (u.scheme == "https" or (u.scheme == "http" and local)): return None
    return f"{u.scheme}://{u.hostname}" + (f":{port}" if port else "")


def logo_of(value: str) -> tuple[str, bytes]:
    """A logo sent as a data: URL (TASK-0145): its type, read from the bytes and not from the URL, and its bytes. No SVG:
    an SVG can carry script. CHAT_LOGO_INVALID otherwise."""
    bad = AppError("CHAT_LOGO_INVALID", max_kb=LOGO_MAX // 1024)
    head, _, body = value.partition(",")
    if not head.startswith("data:") or not head.endswith(";base64") or len(body) > (LOGO_MAX * 4 // 3) + 4: raise bad
    try: data = base64.b64decode(body, validate=True)
    except (binascii.Error, ValueError): raise bad from None
    mime = next((m for sig, m in LOGO_TYPES if data.startswith(sig)), None)
    if mime is None and data[:4] == b"RIFF" and data[8:12] == b"WEBP": mime = "image/webp"
    if mime is None or len(data) > LOGO_MAX: raise bad
    return mime, data


def logo_hash(data: bytes) -> str: return hashlib.sha256(data).hexdigest()[:16]
STEP_EVENTS = ("node_started", "node_finished", "error", "run_waiting")


def answered_by(node_data: Optional[dict]) -> str:
    """Who answers a Human node in a chat (DEC-0054): the person chatting (default) or a reviewer in the Approvals inbox.
    An Agent node's tool approval is always a reviewer's: the person chatting does not approve the agent's own actions."""
    if (node_data or {}).get("agent_of"): return "reviewer"
    v = (node_data or {}).get("answered_by")
    return v if v in ANSWERED_BY else "visitor"


def steps_of(events: list, mode: str) -> list[dict]:
    """The node steps of a run as a chat shows them (DEC-0053): none, labels (node, label, type, status) or full
    (plus duration, input, output and errors)."""
    if mode == "none": return []
    out: dict[str, dict] = {}
    for e in events:
        t, nid = e.get("type"), e.get("node")
        hidden = ("start", "end", "agent", "agent_exit", "agent_join") + (() if mode == "full" else ("agent_model",))  # an Agent shows its tool calls; the join only orders them
        if t not in STEP_EVENTS or not nid or e.get("node_type") in hidden: continue
        key = f"{nid}:{e.get('iteration') or 1}"
        s = out.setdefault(key, {"node": nid, "label": e.get("label") or nid, "type": e.get("node_type") or e.get("kind"), "status": "running"})
        if t == "node_finished": s["status"] = "ok"
        if t == "error": s["status"] = "error"
        if t == "run_waiting": s["status"] = "waiting"  # a Human node that waits for its answer
        step = e.get("agent") if isinstance(e.get("agent"), dict) else None  # what an Agent step did (TASK-0116)
        if step and step.get("kind") == "tool" and step.get("tool"): s["label"] = f"{s['label'].rsplit(' › ', 1)[0]} › {step['tool']}"
        if mode == "full":
            for k in ("duration_ms", "input", "delta", "errors", "code"):
                if k in e: s[k] = e[k]
            if step: s["delta"] = step
            if step and step.get("child_run_id"): s["child_run_id"] = step["child_run_id"]  # a workflow tool's child run (TASK-0136)
            if isinstance(s.get("input"), dict): s["input"] = agents.visible(s["input"])
    return list(out.values())


class ChatSessionService:
    def __init__(self, sessions: ChatSessionRepository, triggers: ChatTriggerRepository, messages: ChatMessageRepository,
                 workflows: WorkflowRepository, runs: RunRepository, access=None, jobs=None):
        self.sessions, self.triggers, self.messages, self.workflows, self.runs, self.access = sessions, triggers, messages, workflows, runs, access
        self.jobs = jobs  # enqueues chat_rating; None in tests that build the service by hand (TASK-0165)

    # ---- settings (the workflow's Chat section) ----
    def settings(self, wid: str, uid: str) -> dict:
        w = self._workflow(wid, uid, P.RUN)
        return self._public(w, self.triggers.web(wid))

    def save_settings(self, wid: str, uid: str, body: dict) -> dict:
        w = self._workflow(wid, uid, P.SHARE)
        if not isinstance(body, dict): raise AppError("CHAT_SETTINGS_INVALID", field="body")
        t = self.triggers.web(wid)
        cur = self._public(w, t); v = {**cur, **{k: body[k] for k in cur if k in body}}
        v = self._check(w, v, t.command if t else None)
        logo = None  # (mime, bytes) of a new logo; "" removes it; the current hash keeps it
        if isinstance(v.get("logo"), str) and v["logo"].startswith("data:"):
            logo = logo_of(v["logo"]); v["logo"] = logo_hash(logo[1])
        elif v.get("logo") not in ("", cur["logo"]): raise AppError("CHAT_LOGO_INVALID", max_kb=LOGO_MAX // 1024)
        taken = self.triggers.find(WEB, WEB, v["slug"])
        if taken is not None and (t is None or taken.id != t.id): raise AppError("CHAT_SLUG_TAKEN", slug=v["slug"])
        cols = {"input_field": v["input_field"], "reply_field": v["reply_field"], "enabled": v["enabled"], "command": v["slug"],
                "settings": json.dumps({k: v[k] for k in DEFAULTS}, ensure_ascii=False)}
        if t is None:
            t = self.triggers.add(WorkflowChatTrigger(id=uuid.uuid4().hex[:10], workflow_id=wid, owner=uid, name="Web chat", channel_id=WEB, place=WEB,
                                                      created=time.time(), **cols))
        else: self.triggers.set_fields(t.id, **cols)
        if logo is not None or (not v["logo"] and cur["logo"]): self.triggers.set_logo(t.id, *(logo or (None, None)))
        return self._public(w, self.triggers.web(wid))

    def logo(self, wid: str, uid: str):
        """The chat's logo for the builder (run right), published or not; CHAT_LOGO_NOT_FOUND when it has none."""
        self._workflow(wid, uid, P.RUN); t = self.triggers.web(wid)
        logo = self.triggers.logo(t.id) if t else None
        if logo is None: raise AppError("CHAT_LOGO_NOT_FOUND")
        return logo

    def _public(self, w, t: Optional[WorkflowChatTrigger]) -> dict:
        fields = self._fields(w)
        guess = lambda names, typ: next((f["name"] for f in fields if f["name"] in names), next((f["name"] for f in fields if f.get("type") == typ), ""))  # noqa: E731
        s = {**DEFAULTS, **(json.loads(t.settings or "{}") if t else {})}
        if t is None: s["messages_field"] = guess(("messages", "history"), "list")
        return {"enabled": bool(t.enabled) if t else False, "slug": t.command if t else w.id.lower(),
                "input_field": t.input_field if t else guess(("message", "input", "question"), "string"),
                "reply_field": t.reply_field if t else guess(("reply", "answer", "output"), "string"), **s}

    def _check(self, w, v: dict, slug_now: Optional[str] = None) -> dict:
        def bad(field): return AppError("CHAT_SETTINGS_INVALID", field=field)
        fields = {f["name"]: f for f in self._fields(w)}
        if v.get("access") not in ACCESS: raise bad("access")
        slug = v.get("slug")  # checked when it changes or the chat is published (an old chat keeps its id-based slug)
        if (slug != slug_now or v["access"] in PUBLIC) and (not isinstance(slug, str) or not SLUG.match(slug) or slug in RESERVED_SLUGS):
            raise AppError("CHAT_SLUG_INVALID")
        for f in ("input_field", "reply_field"):
            if v.get(f) not in fields: raise bad(f)
        m = v.get("messages_field") or ""
        if m and (m not in fields or fields[m].get("type") != "list" or m in (v["input_field"],)): raise bad("messages_field")
        if v.get("steps") not in STEPS: raise bad("steps")
        for k, hi in (("max_turns", MAX_TURNS), ("retention_days", RETENTION_MAX)):
            n = v.get(k)
            if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= hi: raise bad(k)
        n = v.get("daily_limit")
        if isinstance(n, bool) or not isinstance(n, int) or not 0 <= n <= DAILY_MAX: raise bad("daily_limit")
        title, intro = v.get("title"), v.get("intro")
        if not isinstance(title, str) or len(title.strip()) > TITLE_MAX: raise bad("title")
        if not isinstance(intro, str) or len(intro) > INTRO_MAX: raise bad("intro")
        sug = v.get("suggestions")
        if not isinstance(sug, list) or len(sug) > SUGGESTIONS_MAX or any(not isinstance(x, str) or not x.strip() or len(x.strip()) > SUGGESTION_MAX for x in sug):
            raise bad("suggestions")
        raw = v.get("embed_origins")
        if not isinstance(raw, list) or len(raw) > ORIGINS_MAX: raise bad("embed_origins")
        origins = []
        for x in raw:
            o = origin_of(x)
            if o is None: raise AppError("CHAT_EMBED_ORIGIN_INVALID", origin=str(x)[:100])
            if o not in origins: origins.append(o)
        return {**v, "enabled": bool(v.get("enabled")), "messages_field": m, "title": title.strip(), "suggestions": [x.strip() for x in sug],
                "embed_origins": origins}

    @staticmethod
    def _fields(w) -> list[dict]:
        try: state = json.loads(w.data or "{}").get("state") or []
        except (ValueError, AttributeError): state = []
        return [f for f in state if isinstance(f, dict) and isinstance(f.get("name"), str)]

    # ---- sessions ----
    def list(self, wid: str, uid: str) -> list[dict]:
        self._workflow(wid, uid, P.RUN)
        return [self._session(s) for s in self.sessions.list_for(wid, uid)]

    def create(self, wid: str, uid: str) -> dict:
        w = self._workflow(wid, uid, P.RUN); t = self._chat(w.id)
        now = time.time()
        return self._session(self.sessions.add(ChatSession(id=uuid.uuid4().hex[:12], workflow_id=w.id, trigger_id=t.id, channel="studio", owner=uid,
                                                           title="", created=now, updated=now)))

    def get(self, sid: str, uid: str, view: str = "builder") -> dict:
        s, t = self._own(sid, uid)
        return self.view(s, "full" if view != "visitor" else self.steps_mode(t))

    @staticmethod
    def steps_mode(t: WorkflowChatTrigger) -> str:
        return json.loads(t.settings or "{}").get("steps") or DEFAULTS["steps"]

    def view(self, s: ChatSession, mode: str) -> dict:
        """A session's turns, each run's steps (in `mode`) with its first answer, and each turn's rating."""
        sid = s.id
        steps: dict[str, list] = {}
        found: set[str] = set()
        turns = self.sessions.turns(sid)
        ratings = {r.turn_id: r for r in self.sessions.ratings_of(sid)}
        for x in turns:
            if x.role == "assistant" and x.run_id and x.run_id not in steps:
                r = self.runs.get(x.run_id)
                if r is not None: found.add(x.run_id)
                steps[x.run_id] = steps_of(json.loads(r.events or "[]") if r else [], mode)
        out = []
        for x in turns:
            d = self._turn(x)
            d["rating"] = self._rating(ratings[x.id]) if x.id in ratings else None
            if x.role == "assistant": d["run_exists"] = bool(x.run_id and x.run_id in found)
            if x.role == "assistant" and x.run_id in steps:
                d["steps"] = steps.pop(x.run_id)  # a run's steps go with its first answer
            out.append(d)
        return {**self._session(s), "steps_mode": mode, "turns": out}

    def visitors(self, wid: str, uid: str, thumbs_down: bool = False) -> list[dict]:
        """The published page's chats, for builders with the run right (DEC-0067 decision 8): no visitor ids or names.
        `thumbs_down` keeps chats with a thumbs down (DEC-0070)."""
        self._workflow(wid, uid, P.RUN); t = self.triggers.web(wid)
        if t is None: return []
        rows = self.sessions.list_public(t.id, thumbs_down=thumbs_down)
        down = self.sessions.down_sessions([s.id for s in rows])
        return [{**self._session(s), "thumbs_down": s.id in down} for s in rows]

    def rating_totals(self, wid: str, uid: str) -> dict:
        """Up and down counts whose rating changed in the last 7 and 30 days (DEC-0070)."""
        self._workflow(wid, uid, P.RUN); now = time.time()
        return {"d7": self.sessions.rating_counts(wid, now - 7 * 86400), "d30": self.sessions.rating_counts(wid, now - 30 * 86400)}

    def rate(self, s: ChatSession, tid: str, value, comment) -> dict:
        """Set the session owner's rating of one finished answer. The last write wins (one row)."""
        turn = self.sessions.turn(tid) if isinstance(tid, str) else None
        if turn is None or turn.session_id != s.id: raise AppError("CHAT_TURN_NOT_FOUND")
        if turn.role != "assistant" or turn.status not in RATEABLE: raise AppError("CHAT_RATING_NOT_ALLOWED")
        if value not in ("up", "down"): raise AppError("CHAT_RATING_INVALID", field="value")
        if comment is None:
            prev = self.sessions.rating(tid)
            text = prev.comment if prev is not None and value == "down" else ""
        elif not isinstance(comment, str):
            raise AppError("CHAT_RATING_INVALID", field="comment")
        else:
            text = comment.strip()
        if value == "up" and text: raise AppError("CHAT_RATING_INVALID", field="comment")
        if len(text) > COMMENT_MAX: raise AppError("CHAT_RATING_INVALID", field="comment")
        now = time.time()
        row = self.sessions.upsert_rating(ChatRating(turn_id=tid, session_id=s.id, workflow_id=s.workflow_id, value=value,
                                                     comment=text, created=now, updated=now))
        if self.jobs is not None: self.jobs.enqueue({"kind": "chat_rating", "turn_id": tid})
        return self._rating(row)

    def unrate(self, s: ChatSession, tid: str) -> dict:
        turn = self.sessions.turn(tid) if isinstance(tid, str) else None
        if turn is None or turn.session_id != s.id: raise AppError("CHAT_TURN_NOT_FOUND")
        self.sessions.delete_rating(tid)
        return {"ok": True}

    def rate_owned(self, sid: str, tid: str, uid: str, value, comment) -> dict:
        s, _t = self._own(sid, uid)
        return self.rate(s, tid, value, comment)

    def unrate_owned(self, sid: str, tid: str, uid: str) -> dict:
        s, _t = self._own(sid, uid)
        return self.unrate(s, tid)

    def visitor_session(self, wid: str, sid: str, uid: str) -> dict:
        self._workflow(wid, uid, P.RUN); s = self.sessions.get(sid)
        if s is None or s.workflow_id != wid or s.channel not in ("web", "embed"): raise AppError("CHAT_SESSION_NOT_FOUND")
        return self.view(s, "full")

    def delete(self, sid: str, uid: str) -> dict:
        self._own(sid, uid); self.sessions.delete(sid); return {"ok": True}

    # ---- a message (RunService.plan, over the run socket) ----
    def input_for(self, uid: str, sid: str, message) -> dict:
        """{workflow_id, input} for the next message, checked; nothing is written yet."""
        s, t = self._own(sid, uid, P.RUN)
        return self.prepare(s, t, message)

    def prepare(self, s: ChatSession, t: WorkflowChatTrigger, message) -> dict:
        """The run input of a message in session `s`, checked: the input field, and the history in the messages field."""
        sid = s.id
        if not t.enabled: raise AppError("CHAT_NOT_ENABLED")
        if not isinstance(message, str) or not message.strip(): raise AppError("CHAT_MESSAGE_EMPTY")
        if len(message) > TEXT_MAX: raise AppError("CHAT_MESSAGE_TOO_LONG", max=TEXT_MAX)
        last = self._turns(sid)
        if last and last[-1].status == "waiting": raise AppError("CHAT_RUN_WAITING")  # answer the question first
        w = self.workflows.get(s.workflow_id)
        st = json.loads(t.settings or "{}"); fields = {f["name"]: f for f in self._fields(w)}
        text = message.strip()
        inp = {t.input_field: [text] if (fields.get(t.input_field) or {}).get("type") == "list" else text}
        if (mf := st.get("messages_field")): inp[mf] = self.history(sid, int(st.get("max_turns") or DEFAULTS["max_turns"])) + [{"role": "user", "content": text}]
        if size(inp) > config.input_max(): raise AppError("RUN_INPUT_TOO_LARGE", max_kb=config.input_max() // 1024)
        return {"workflow_id": s.workflow_id, "input": inp, "text": text}

    def history(self, sid: str, max_turns: int) -> list[dict]:
        """The last `max_turns` exchanges as [{role, content}] (DEC-0052): the person's messages and the finished answers."""
        rows = [x for x in self._turns(sid) if x.role == "user" or (x.role == "assistant" and x.status == "ok")]
        msgs = [{"role": x.role, "content": x.text} for x in rows]
        return msgs[-2 * max_turns:]

    def record(self, uid: str, sid: str, text: str, rid: str) -> None:
        """The person's turn and the reply-once record, once the run is planned."""
        s, t = self._own(sid, uid, P.RUN)
        self.write(s, t, text, rid, uid)

    def write(self, s: ChatSession, t: WorkflowChatTrigger, text: str, rid: str, sender: str) -> None:
        sid, now = s.id, time.time()
        turn = self.sessions.add_turn(ChatTurn(id=uuid.uuid4().hex[:12], session_id=sid, run_id=rid, role="user", text=text, status="ok", created=now))
        self.messages.add_once(ChatMessage(id=uuid.uuid4().hex[:12], channel_id=WEB, key=turn.id, trigger_id=t.id, workflow_id=s.workflow_id, kind=WEB,
                                           team="", sender=sender, text=text, ref=json.dumps({"session": sid}), status="started", run_id=rid, created=now))
        self.sessions.set_fields(sid, last_run_id=rid, **({"title": text[:TITLE_MAX]} if not s.title else {}))
        self.triggers.set_fields(t.id, last_message=now, last_run_id=rid)

    def check_answer(self, uid: str, sid: str, rid: str) -> None:
        """A visitor answer from the chat: the run is this session's and its Human node is answered by the visitor."""
        self._own(sid, uid, P.RUN)
        turn = next((x for x in reversed(self._turns(sid)) if x.run_id == rid), None)
        if turn is None: raise AppError("RUN_NOT_FOUND")
        if turn.status == "waiting" and turn.answered_by == "reviewer": raise AppError("CHAT_ANSWER_BY_REVIEWER")

    # ---- a run settled (ChatRunService.on_settled, once per state) ----
    def answer(self, m: ChatMessage, r: Run, res: dict) -> None:
        sid = (json.loads(m.ref or "{}") or {}).get("session")
        t = self.triggers.get(m.trigger_id)
        if not sid or self.sessions.get(sid) is None or t is None: return
        turn = ChatTurn(id=uuid.uuid4().hex[:12], session_id=sid, run_id=r.id, role="assistant", status=r.status, created=time.time())
        if r.status == "ok":
            v = (res.get("final_state") or {}).get(t.reply_field)
            turn.text = v if isinstance(v, str) else ("" if v is None else json.dumps(v, ensure_ascii=False))
        elif r.status == "waiting":
            ev = next((e for e in reversed(json.loads(r.events or "[]")) if e.get("type") == "run_waiting"), {})
            node = (res.get("waiting") or {}).get("node") or ev.get("node")
            wf = (json.loads(r.checkpoint or "{}") or {}).get("workflow") or {}
            data = next((n.get("data") for n in wf.get("nodes") or [] if n.get("id") == node), None)
            turn.text, turn.node, turn.answered_by = ev.get("prompt") or "", node, answered_by(data)
        else:
            err = res.get("error"); turn.code = (err or {}).get("code") if isinstance(err, dict) else None
            turn.text = ((err or {}).get("message") if isinstance(err, dict) else err) or ""
        self.sessions.add_turn(turn)

    # ---- retention (the worker's maintenance loop) ----
    def cleanup(self) -> int:
        """Deletes sessions idle for longer than their chat's retention_days (DEC-0052)."""
        n, now = 0, time.time()
        for t in self.triggers.webs():
            days = int((json.loads(t.settings or "{}") or {}).get("retention_days") or DEFAULTS["retention_days"])
            n += self.sessions.delete_idle(t.id, now - days * 86400)
        return n

    # ---- helpers ----
    def _workflow(self, wid: str, uid: str, action: str):
        if self.access is not None: return self.access.workflow(wid, uid, action)
        w = self.workflows.get_owned(wid, uid)
        if w is None: raise AppError("WORKFLOW_NOT_FOUND")
        return w

    def _chat(self, wid: str) -> WorkflowChatTrigger:
        t = self.triggers.web(wid)
        if t is None or not t.enabled: raise AppError("CHAT_NOT_ENABLED")
        return t

    def _own(self, sid: str, uid: str, action: str = P.VIEW) -> tuple[ChatSession, WorkflowChatTrigger]:
        s = self.sessions.get(sid)
        if s is None or s.owner != uid: raise AppError("CHAT_SESSION_NOT_FOUND")
        self._workflow(s.workflow_id, uid, action)
        t = self.triggers.get(s.trigger_id)
        if t is None: raise AppError("CHAT_NOT_ENABLED")
        return s, t

    def _turns(self, sid: str) -> list[ChatTurn]: return self.sessions.turns(sid)

    @staticmethod
    def _session(s: ChatSession) -> dict:
        return {"id": s.id, "workflow_id": s.workflow_id, "channel": s.channel, "title": s.title, "last_run_id": s.last_run_id,
                "created": s.created, "updated": s.updated}

    @staticmethod
    def _turn(x: ChatTurn) -> dict:
        return {"id": x.id, "role": x.role, "text": x.text, "status": x.status, "run_id": x.run_id, "node": x.node,
                "answered_by": x.answered_by, "code": x.code, "created": x.created}

    @staticmethod
    def _rating(r: ChatRating) -> dict:
        return {"value": r.value, "comment": r.comment, "updated": r.updated}
