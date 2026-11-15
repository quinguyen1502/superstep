"""Chat-trigger runs: a message to the Slack app or Telegram bot starts a workflow.

receive() runs on the platform's request (Slack wants an answer within 3 s): the message's first word must match a
chat trigger of a connection that verified the request; the message is stored once (the platform's delivery id is
unique per connection, so retries start nothing) and a `chat_message` job is queued. handle() runs on the worker:
it checks the trigger, the sender's verified linked account and its run right, the rate limit and the input size,
then starts a `source="chat"` run owned by the sender's studio user and says so in the thread. on_settled() answers
in the thread when the run finishes, fails or waits. Refusals go to the sender only and are audited.
"""
import asyncio, json, re, time, uuid
from dataclasses import dataclass
from typing import Optional
from ..core import config, permissions as P
from ..core.errors import AppError
from ..core.logging import get_logger
from ..engine import activity
from ..engine.limits import size
from ..models import ApprovalAudit, ChatMessage, Run, WorkflowChatTrigger
from ..repositories import ChatMessageRepository, ChatTriggerRepository, RunRepository, UserRepository, WorkflowRepository
from ..repositories.chat_triggers import WEB
from .approval_channels import ApprovalChannel, IncomingMessage
from .approval_channels.messages import lang_of, text
from .channel_service import ChannelService
from .job_queue import JobQueue
from .trigger_service import run_result
from . import event_bindings

log = get_logger("chat")
COMMAND = re.compile(r"/?([A-Za-z0-9][\w-]{0,31})(?:[\s:,]+|$)(.*)", re.S)  # the first word, then the text
VALUE_MAX = 3000  # characters of the reply field in the thread


@dataclass
class _Job:
    m: ChatMessage
    a: ApprovalChannel
    secrets: dict
    trigger: Optional[WorkflowChatTrigger]
    workflow: Optional[object]
    uid: Optional[str]
    code: Optional[str] = None


class ChatRunService:
    def __init__(self, messages: ChatMessageRepository, triggers: ChatTriggerRepository, channels: ChannelService, users: UserRepository,
                 workflows: WorkflowRepository, runs: RunRepository, jobs: JobQueue, access=None, limiter=None, web=None):
        self.messages, self.triggers, self.channels, self.users = messages, triggers, channels, users
        self.workflows, self.runs, self.jobs, self.access, self.limiter = workflows, runs, jobs, access, limiter
        self.approvals = channels.repo  # identities and the approval audit log
        self.web = web  # ChatSessionService: answers of the studio / web chat

    # ---- on the platform's request ----
    def events(self, kind: str, headers: dict, body: bytes):
        """The events URL (Slack): the URL check, else a message from one of the claimed workspace's connections."""
        a = self.channels.adapter(kind)
        if not a.events_path: raise AppError("CHANNEL_KIND_UNSUPPORTED", kind=kind)
        challenge = a.event_challenge(body)
        if challenge is not None: return challenge  # echoing the platform's own value reveals nothing
        m = a.handle_message(body)
        if m is None: return {"outcome": "ignored"}
        rows = self.channels.verified(a, m.team, {k.lower(): v for k, v in headers.items()}, body)
        if not rows: raise AppError("CHANNEL_SIGNATURE_INVALID")
        return self.receive(rows, m)

    def receive(self, rows: list, m: IncomingMessage) -> dict:
        """rows: the (connection, secrets) the request verified against. Stores and queues a message that matches a trigger."""
        out = self._receive(rows, m)
        if rows: activity.emit("channel", kind=rows[0][0].kind, direction="in", status=out.get("outcome") or "ok")
        return out

    def _receive(self, rows: list, m: IncomingMessage) -> dict:
        hit = COMMAND.match(m.text); found = None
        for c, _ in rows if hit else []:
            if (t := self.triggers.find(c.id, m.place, hit.group(1).lower())) is not None: found = (c, t); break
        if found is None:
            for c, _ in rows:
                t = self.triggers.find(c.id, m.place, "*")
                if t is not None and event_bindings.settings(t) is not None: return self._receive_event(c, t, m)
            return {"outcome": "ignored"}  # chatter, or no binding for this place
        c, t = found
        row = ChatMessage(id=uuid.uuid4().hex[:12], channel_id=c.id, key=m.key or uuid.uuid4().hex, trigger_id=t.id, workflow_id=t.workflow_id,
                          kind=c.kind, team=m.team, sender=m.sender, text=hit.group(2).strip(), ref=json.dumps(m.ref), status="queued", created=time.time())
        if not self.messages.add_once(row): return {"outcome": "duplicate"}  # a platform retry
        self.triggers.set_fields(t.id, last_message=row.created)
        self.jobs.enqueue({"kind": "chat_message", "message_id": row.id})
        return {"outcome": "queued"}

    def _receive_event(self, channel, trigger, message):
        """Explicit run-as-owner admission. Persist dedupe identity and queued run in one transaction."""
        policy = event_bindings.settings(trigger)
        event = event_bindings.envelope(channel.kind, message)
        if not trigger.enabled or not event_bindings.admitted(policy, message, event): return {"outcome": "ignored"}
        owner = trigger.owner
        if not self.channels.usable(owner, channel) or (channel.scope == "org" and not self.channels.org_allowed(owner)):
            return {"outcome": "ignored"}
        workflow = self.workflows.get(trigger.workflow_id)
        if workflow is None or not self._may(workflow, owner, P.SHARE) or not self._may(workflow, owner, P.RUN):
            self.triggers.set_fields(trigger.id, enabled=False, note="access"); return {"outcome": "ignored"}
        try:
            data = json.loads(workflow.data or "{}")
            policy = event_bindings.validate(policy, {f["name"] for f in data.get("state", []) if isinstance(f, dict) and isinstance(f.get("name"), str)})
            inp = event_bindings.map_input(policy, event, data)
        except (AppError, ValueError, KeyError): return {"outcome": "ignored"}
        rid, now = uuid.uuid4().hex[:10], time.time()
        row = ChatMessage(id=uuid.uuid4().hex[:12], channel_id=channel.id, key=message.key, trigger_id=trigger.id, workflow_id=workflow.id,
                          kind=channel.kind, team=message.team, sender=message.sender, text=message.text,
                          ref=json.dumps({**message.ref, "event": event}), status="started", run_id=rid, created=now)
        run = Run(id=rid, workflow_id=workflow.id, input=json.dumps(inp, ensure_ascii=False), events="[]", status="queued", started=now,
                  owner=owner, source="chat")
        if not self.messages.add_event_once(row, run):
            # A previous delivery may have committed then lost the queue response. Requeue the persisted job,
            # never the retry's payload; the normal run claim prevents two workers from executing it.
            previous = self.messages.by_key(channel.id, message.key)
            saved = self.runs.get(previous.run_id) if previous and previous.run_id else None
            if saved is not None and saved.status == "queued":
                self.jobs.enqueue({"run_id": saved.id, "workflow_id": saved.workflow_id, "owner": saved.owner,
                                   "input": json.loads(saved.input), "callback_url": None, "token_id": None, "source": "chat"})
            return {"outcome": "duplicate"}
        self.triggers.set_fields(trigger.id, last_message=now, last_run_id=rid)
        self._audit(owner, row, "event_started", actor=message.sender, run_id=rid)
        # Event workflows own their replies through tools; no automatic processing/success message is sent here.
        self.jobs.enqueue({"run_id": rid, "workflow_id": workflow.id, "owner": owner, "input": inp,
                           "callback_url": None, "token_id": None, "source": "chat"})
        return {"outcome": "queued"}

    # ---- on the worker ----
    async def handle(self, mid: str) -> Optional[str]:
        """Check, then start the run or refuse. Returns the run id."""
        job = await asyncio.to_thread(self._check, mid)
        if job is None: return None
        if job.code is None and not await self._rate_ok(job): job.code = "RATE_LIMITED"
        return await asyncio.to_thread(self._start if job.code is None else self._refuse, job)

    def _check(self, mid: str) -> Optional[_Job]:
        m = self.messages.get(mid) if self.messages.claim(mid) else None
        c = self.channels.repo.channel(m.channel_id) if m is not None else None
        if c is None or c.kind not in self.channels.adapters: return None  # handled already, or the connection is gone (nowhere to answer)
        t, w = self.triggers.get(m.trigger_id), self.workflows.get(m.workflow_id)
        uid = self.approvals.user_for(m.kind, m.sender, m.team)
        job = _Job(m, self.channels.adapter(c.kind), self.channels.secrets(c), t, w, uid)
        if t is None or w is None: job.code = "WORKFLOW_NOT_FOUND"
        elif not t.enabled: job.code = "CHAT_TRIGGER_OFF"
        elif not self._may(w, t.owner, P.SHARE):  # the creator lost the share right: stop it, as the scheduler does
            self.triggers.set_fields(t.id, enabled=False, note="access"); job.code = "CHAT_TRIGGER_OFF"
        elif uid is None: job.code = "CHAT_IDENTITY_UNVERIFIED" if self.approvals.linked(m.kind, m.sender, m.team) else "CHAT_IDENTITY_UNKNOWN"
        elif not self._may(w, uid, P.RUN): job.code = "CHAT_FORBIDDEN"
        elif size(self._input(w, t, m.text)) > config.input_max(): job.code = "RUN_INPUT_TOO_LARGE"
        return job

    def _may(self, w, uid: str, action: str) -> bool:
        return self.access.may(w.id, uid, action) if self.access is not None else w.owner == uid

    async def _rate_ok(self, job: _Job) -> bool:
        limit = config.chat_trigger_rate_limit()
        if self.limiter is None or not limit: return True
        ok, _ = await self.limiter.hit(f"chat:{job.trigger.id}:{job.m.sender}", limit, config.trigger_rate_window())
        return ok

    @staticmethod
    def _input(w, t: WorkflowChatTrigger, msg: str) -> dict:
        """{input_field: text}; a list field gets a one-item list."""
        try: state = json.loads(w.data or "{}").get("state") or []
        except ValueError: state = []
        typ = next((f.get("type") for f in state if isinstance(f, dict) and f.get("name") == t.input_field), None)
        return {t.input_field: [msg] if typ == "list" else msg}

    def _start(self, job: _Job) -> str:
        m, t, w = job.m, job.trigger, job.workflow
        rid = uuid.uuid4().hex[:10]; inp = self._input(w, t, m.text)
        self.runs.add(Run(id=rid, workflow_id=w.id, input=json.dumps(inp, ensure_ascii=False), events="[]", status="queued", started=time.time(),
                          owner=job.uid, source="chat"))
        self.messages.set_fields(m.id, status="started", run_id=rid); self.triggers.set_fields(t.id, last_run_id=rid)
        self._audit(t.owner, m, "chat_started", run_id=rid, actor=job.uid)
        lang = self._lang(job.uid)
        self._say(job.a, job.secrets, m, self._with_link(lang, text(lang, "chat_started", workflow=w.name, run=rid), w.id, rid))  # before the run can settle
        self.jobs.enqueue({"run_id": rid, "workflow_id": w.id, "owner": job.uid, "input": inp, "callback_url": None, "token_id": None, "source": "chat"})
        return rid

    def _refuse(self, job: _Job) -> None:
        m = job.m; owner = job.trigger.owner if job.trigger else (job.workflow.owner if job.workflow else None)
        self.messages.set_fields(m.id, status="refused", code=job.code)
        if owner: self._audit(owner, m, "chat_refused", code=job.code, actor=job.uid)
        lang = self._lang(job.uid or owner)  # the sender's language when we know who they are
        try: job.a.reply_private(job.secrets, json.loads(m.ref), m.sender, text(lang, job.code, kind=job.a.label))
        except AppError as e: log.warning("chat refusal %s via %s not delivered: %s", job.code, m.kind, e.message)

    # ---- when a chat run settles (RunService.settled) ----
    def on_settled(self, rid: str) -> None:
        m, r = self.messages.by_run(rid), self.runs.get(rid)
        if m is None or r is None or r.status in ("queued", "running"): return
        if "event" in json.loads(m.ref or "{}"): return  # event workflows send their own confirmed tool replies
        res = run_result(r); waiting = res["waiting"] or {}
        key = f"waiting:{waiting.get('node')}" if r.status == "waiting" else r.status
        if m.replied == key or not self.messages.mark_replied(m.id, m.replied, key): return  # this state was answered already
        if m.kind == WEB:  # the web chat writes a turn instead of posting to a platform
            if self.web is not None: self.web.answer(m, r, res)
            return
        c = self.channels.repo.channel(m.channel_id)
        if c is None or c.kind not in self.channels.adapters: return
        w = self.workflows.get(r.workflow_id); name = w.name if w else r.workflow_id; lang = self._lang(r.owner)
        if r.status == "ok":
            t = self.triggers.get(m.trigger_id)
            msg = text(lang, "chat_finished", workflow=name, value=self._value((res["final_state"] or {}).get(t.reply_field) if t else None, lang))
        elif r.status == "waiting":
            ev = next((e for e in reversed(json.loads(r.events or "[]")) if e.get("type") == "run_waiting"), {})
            msg = text(lang, "chat_waiting", workflow=name, node=ev.get("label") or waiting.get("node"))
        elif r.status == "error":
            err = res["error"]; msg = text(lang, "chat_failed", workflow=name, error=(err or {}).get("message") if isinstance(err, dict) else err or "?")
        else: msg = text(lang, "chat_ended", workflow=name, status=r.status)
        self._say(self.channels.adapter(c.kind), self.channels.secrets(c), m, self._with_link(lang, msg, r.workflow_id, rid))

    @staticmethod
    def _value(v, lang: str) -> str:
        if v is None or v == "": return text(lang, "chat_empty")
        s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, separators=(",", ":"))
        return s if len(s) <= VALUE_MAX else s[:VALUE_MAX - 1] + "…"

    # ---- run history (RunService.history) ----
    def runs_info(self, rids: list[str]) -> dict[str, dict]:
        """{run id: {kind, sender, trigger}} for the history's Chat badge."""
        names: dict[str, Optional[str]] = {}
        def name(tid):
            if tid not in names: t = self.triggers.get(tid); names[tid] = t.name if t else None
            return names[tid]
        return {m.run_id: {"kind": m.kind, "sender": m.sender, "trigger": name(m.trigger_id)} for m in self.messages.by_runs(rids)}

    # ---- helpers ----
    def _lang(self, uid: Optional[str]) -> str: return lang_of(self.users.get_by_id(uid)) if uid else "en"

    @staticmethod
    def _with_link(lang: str, msg: str, wid: str, rid: str) -> str:
        base = config.public_url()
        return f"{msg}\n{text(lang, 'chat_open', link=f'{base}/workflows/{wid}?run={rid}')}" if base else msg

    def _say(self, a: ApprovalChannel, secrets: dict, m: ChatMessage, msg: str) -> None:
        try:
            a.reply(secrets, json.loads(m.ref), msg); activity.emit("channel", kind=m.kind, direction="out", status="ok")
        except AppError as e:
            activity.emit("channel", kind=m.kind, direction="out", status=e.code)
            log.warning("chat reply via %s failed: %s", m.kind, e.message)

    def _audit(self, owner: str, m: ChatMessage, action: str, code=None, actor=None, run_id=None) -> None:
        try: self.approvals.audit(ApprovalAudit(id=uuid.uuid4().hex[:12], owner=owner, request_id=None, run_id=run_id, workflow_id=m.workflow_id,
                                                kind=m.kind, action=action, code=code, actor_id=actor, external_id=m.sender, created=time.time()))
        except Exception: log.exception("writing a chat audit entry failed")
