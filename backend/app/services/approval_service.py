"""Human-in-the-loop approval through external channels (TASK-0022, DEC-0019).

Flow: a run pauses at a Human node whose `data.approval` names a channel -> `on_waiting` posts a message with
Approve/Reject buttons (signed, single-use, expiring tokens) -> the platform calls back -> `handle_callback` verifies
the request, maps the channel user to a studio user, checks they are the run owner or a listed approver, records the
decision (compare-and-set, so a token works once), queues a `resume` job and edits the original message.
Every step lands in the audit log. Without a configured channel everything is a no-op.
"""
import base64, hashlib, hmac, json, secrets as pysecrets, threading, time, uuid
from typing import Callable, Optional
from ..core import config, crypto
from ..core.errors import AppError
from ..core.logging import get_logger
from ..engine import deadlines
from ..models import ApprovalAudit, ApprovalRequest, ApprovalWait
from ..repositories import ApprovalRepository, RunRepository, UserRepository, WorkflowRepository
from .approval_channels import ApprovalChannel, ApprovalMessage
from .approval_channels.messages import lang_of, text
from .channel_service import ChannelService
from .job_queue import enqueue_resume

log = get_logger("approvals")
DECISIONS = {"a": "approved", "r": "rejected"}
CLOSE_TEXTS = ("answered", "cancelled", "expired", "deadline_approved", "deadline_rejected")  # chat texts close_run edits messages to
PROMPT_MAX = 4000  # characters of the question kept on a waiting step (the inbox shows it)
BACKGROUND = True  # send/edit messages off the request thread; tests switch it off for determinism


class ApprovalService:
    def __init__(self, repo: ApprovalRepository, users: UserRepository, workflows: WorkflowRepository, runs: RunRepository, channels: ChannelService,
                 enqueue: Optional[Callable[[dict], None]] = None, background: Optional[bool] = None, limiter=None, notifier=None,
                 chat: Optional[Callable[[], object]] = None):
        self.repo, self.users, self.workflows, self.runs, self.channels, self.enqueue = repo, users, workflows, runs, channels, enqueue
        self.notifier = notifier  # NotificationService (optional): deadline reminders and escalations (TASK-0066)
        self.limiter = limiter  # RateLimiter for the public callbacks (None = no limit)
        self.chat = chat  # -> ChatRunService (optional): messages on the same webhook start chat-trigger runs (TASK-0075)
        self.adapters = channels.adapters
        self.background = BACKGROUND if background is None else background

    def adapter(self, kind: str) -> ApprovalChannel: return self.channels.adapter(kind)
    def _lang(self, uid: Optional[str]) -> str: return lang_of(self.users.get_by_id(uid)) if uid else "en"
    def _secrets(self, c) -> dict: return self.channels.secrets(c)

    # ---- tokens: "<a|r>.<request id>.<hmac>" (fits Telegram's 64-byte callback_data) ----
    @staticmethod
    def _sig(r: ApprovalRequest, d: str) -> str:
        msg = f"{r.id}:{d}:{r.nonce}:{int(r.expires)}".encode()
        return base64.urlsafe_b64encode(hmac.new(crypto.derive_key("approval-token"), msg, hashlib.sha256).digest()[:16]).decode().rstrip("=")

    def token(self, r: ApprovalRequest, d: str) -> str: return f"{d}.{r.id}.{self._sig(r, d)}"

    def _parse(self, token: str) -> tuple[Optional[ApprovalRequest], Optional[str]]:
        parts = (token or "").split(".")
        if len(parts) != 3 or parts[0] not in DECISIONS: return None, None
        r = self.repo.request(parts[1])
        if r is None or not hmac.compare_digest(self._sig(r, parts[0]), parts[2]): return None, None
        return r, DECISIONS[parts[0]]

    # ---- audit ----
    def _audit(self, owner, kind, action, r: Optional[ApprovalRequest] = None, code=None, actor=None, external=None, run_id=None, wid=None):
        try: self.repo.audit(ApprovalAudit(id=uuid.uuid4().hex[:12], owner=owner, request_id=r.id if r else None, run_id=r.run_id if r else run_id,
                                           workflow_id=r.workflow_id if r else wid, kind=kind, action=action, code=code, actor_id=actor,
                                           external_id=external, created=time.time()))
        except Exception: log.exception("writing an approval audit entry failed")

    def audit_log(self, uid: str) -> list[dict]:
        names, emails = {}, {}
        def name(wid):
            if wid and wid not in names: w = self.workflows.get(wid); names[wid] = w.name if w else None
            return names.get(wid)
        def email(u):
            if u and u not in emails: x = self.users.get_by_id(u); emails[u] = x.email if x else None
            return emails.get(u)
        return [{"id": e.id, "at": e.created, "kind": e.kind, "action": e.action, "code": e.code, "run_id": e.run_id, "workflow_id": e.workflow_id,
                 "workflow_name": name(e.workflow_id), "actor": email(e.actor_id), "external_id": e.external_id} for e in self.repo.audit_for(uid)]

    # ---- producer: a run paused at a Human node ----
    def on_waiting(self, rid: str, owner: str, wid: Optional[str], workflow: dict, ev: dict) -> None:
        node = next((n for n in workflow.get("nodes") or [] if n.get("id") == ev.get("node")), None)
        cfg = ((node or {}).get("data") or {}).get("approval") or {}
        target = str(cfg.get("target") or "").strip()
        kind = cfg.get("channel"); needs_target = self.adapters[kind].target_required if kind in self.adapters else True
        external = bool(cfg.get("channel_id") or kind) and not (needs_target and not target)
        w = self._wait(rid, owner, wid, ev, cfg, external, (node or {}).get("data") or {})
        if not external: return  # this node does not use an external channel
        job = lambda: self._request(rid, owner, wid, node, cfg, target, ev, w.due_at)  # noqa: E731
        threading.Thread(target=job, daemon=True).start() if self.background else job()

    def _approver_ids(self, cfg: dict) -> list[str]:
        """The node's approvers (e-mails) as studio user ids; unknown addresses are dropped."""
        return [u.id for e in cfg.get("approvers") or [] if isinstance(e, str) and (u := self.users.get_by_email(e.strip().lower()))]

    def _wait(self, rid, owner, wid, ev, cfg, external: bool, data: dict) -> ApprovalWait:
        """The waiting step the Approvals inbox lists (TASK-0065), written for every Human node, channel or not, with the
        node's deadline from the run's own workflow snapshot (TASK-0066)."""
        kind = (cfg.get("channel") or ((ch := self.repo.channel(str(cfg["channel_id"]))) and ch.kind) or None) if external else None
        now = time.time(); dl = deadlines.parse(data)
        return self.repo.add_wait(ApprovalWait(
            id=uuid.uuid4().hex[:12], run_id=rid, node_id=str(ev.get("node") or ""), owner=owner, workflow_id=wid, label=ev.get("label") or None,
            prompt=(ev.get("prompt") or "")[:PROMPT_MAX] or None, channel=kind, status="waiting", created=now,
            approval=json.dumps(cfg) if external else None, deadline=json.dumps(dl) if dl else None, reminders=0,
            due_at=now + dl["after"] if dl else None, next_remind_at=now + dl["remind_every"] if dl and dl["remind_every"] else None),
            self._approver_ids(cfg))

    def may_answer(self, uid: str, w: ApprovalWait) -> bool:
        return uid == w.owner or uid in self.repo.wait_approvers(w.id)

    def claim(self, rid: str) -> bool:
        """First answer wins (DEC-0043): close the run's open waiting step. True when this caller closed it, or when the run
        paused before waiting steps existed (no row at all)."""
        return self.repo.close_wait(rid, "answered") or self.repo.latest_wait(rid) is None

    def _request(self, rid, owner, wid, node, cfg, target, ev, due: Optional[float] = None) -> Optional[ApprovalRequest]:
        """Send one approval message. Its buttons expire after STUDIO_APPROVAL_TTL, or at the step's deadline if sooner."""
        if self.channels.org_denied(owner, cfg):  # admin policy (TASK-0029)
            self._audit(owner, cfg.get("channel") or "channel", "not_configured", code="ORG_RESOURCE_NOT_ALLOWED", run_id=rid, wid=wid); return None
        c = self.channels.for_node(owner, cfg)
        if c is None:
            kind = cfg.get("channel") or (ch.kind if (ch := self.repo.channel(str(cfg.get("channel_id")))) else "channel")
            self._audit(owner, kind, "not_configured", code="CHANNEL_NOT_FOUND", run_id=rid, wid=wid); return None
        kind = c.kind
        approvers = self._approver_ids(cfg)
        r = self.repo.add_request(ApprovalRequest(id=uuid.uuid4().hex[:12], run_id=rid, node_id=node["id"], owner=owner, workflow_id=wid, channel_id=c.id,
                                                  kind=kind, target=target, approvers=json.dumps(approvers), nonce=pysecrets.token_hex(8),
                                                  expires=min(time.time() + config.approval_ttl(), due or float("inf")), status="pending", created=time.time()))
        w = self.workflows.get(wid) if wid else None; lang = self._lang(owner)
        lines = [w and text(lang, "workflow", v=w.name), text(lang, "step", v=ev.get("label") or node["id"]), ev.get("prompt") and text(lang, "question", v=ev["prompt"]),
                 text(lang, "run", v=rid), text(lang, "expires", v=time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime(r.expires)))]
        link = f"{config.public_url()}/workflows/{wid}?run={rid}" if config.public_url() and wid else None
        msg = ApprovalMessage(text(lang, "title"), [x for x in lines if x], link, self.token(r, "a"), self.token(r, "r"),
                              text(lang, "approve"), text(lang, "reject"), text(lang, "open"))
        try:
            ref = self.adapter(kind).send_request(self._secrets(c), target, msg)
            self.repo.set_ref(r.id, ref); self._audit(owner, kind, "requested", r)
        except AppError as e:
            self.repo.set_ref(r.id, None, "failed"); self._audit(owner, kind, "send_failed", r, code=e.code)
            log.warning("approval request for run %s via %s failed: %s", rid, kind, e.message)
        return r

    # ---- platform callback ----
    async def check_rate(self, ip: str, kind: str, cid: Optional[str], body: bytes) -> None:
        """Fixed-window limits on the unauthenticated callback endpoints, before any decryption or signature work:
        per client IP (STUDIO_CALLBACK_RATE_LIMIT_IP) and per connection (STUDIO_CALLBACK_RATE_LIMIT_CHANNEL; the
        claimed Slack team on the shared URL). 429 RATE_LIMITED + Retry-After."""
        if self.limiter is None: return
        window = config.callback_rate_window()
        target = cid or (f"team:{self.adapter(kind).route_key(body)}" if kind in self.adapters else None) or "shared"
        for key, limit in ((f"approval-cb:ip:{ip}", config.callback_rate_limit_ip()), (f"approval-cb:ch:{kind}:{target}", config.callback_rate_limit_channel())):
            if not limit: continue
            ok, retry = await self.limiter.hit(key, limit, window)
            if not ok:
                log.warning("approval callback rate limited (%s)", key)
                raise AppError("RATE_LIMITED", headers={"Retry-After": str(retry)}, retry_after=retry)

    def _connection(self, a: ApprovalChannel, cid: Optional[str], headers: dict, body: bytes, cb) -> tuple:
        """The connection a callback authenticates against -> (row, secrets). Per-connection URL: that row. Shared URL
        (cid None): the rows of the claimed account (Slack team_id) whose secret verifies the signature; when several
        do (the same app connected twice), the one the button's request was sent through."""
        if cid is not None:
            c = self.repo.channel(cid)
            if c is None or c.kind != a.kind: raise AppError("CHANNEL_NOT_FOUND")
            sec = self._secrets(c); a.verify(sec, headers, body); return c, sec  # 401 CHANNEL_SIGNATURE_INVALID
        ok = self.channels.verified(a, a.route_key(body) if a.shared_callback else None, headers, body)
        if not ok: raise AppError("CHANNEL_SIGNATURE_INVALID")  # unknown team: same 401 as a bad signature
        want = (cb.token.split(".") + ["", ""])[1] if cb else ""
        req = self.repo.request(want) if want else None
        return next(((c, sec) for c, sec in ok if req is not None and c.id == req.channel_id), ok[0])

    def challenge(self, kind: str, cid: str, query: dict) -> str:
        a = self.adapter(kind); c = self.repo.channel(cid)
        if c is None or c.kind != a.kind: raise AppError("CHANNEL_NOT_FOUND")
        answer = a.challenge(self._secrets(c), query)
        if answer is None: raise AppError("CHANNEL_NOT_FOUND")
        return answer

    def handle_callback(self, kind: str, cid: Optional[str], headers: dict, body: bytes) -> dict:
        """cid None = the shared callback URL of the kind (Slack: routed by team_id)."""
        a = self.adapter(kind); headers = {k.lower(): v for k, v in headers.items()}
        cb = a.handle_callback(body)  # parsing only; nothing is trusted before the signature check below
        c, sec = self._connection(a, cid, headers, body, cb)
        if cb is None:  # not a button press: a message to the bot (Telegram's one webhook) may start a run
            m = a.handle_message(body) if a.chat and self.chat is not None else None
            return self.chat().receive([(c, sec)], m) if m else {"outcome": "ignored"}
        team = (c.team_id or "") if a.per_team else ""
        code, r, decision = self.decide(kind, c.id, cb.token, cb.external_user, team)
        presser = self.repo.user_for(kind, cb.external_user, team) if cb.external_user else None
        mine = self._lang(presser or (r.owner if r else None))  # private answers: the presser's language, else the owner's
        if code:
            a.acknowledge(sec, cb, text(mine, code, kind=a.label), accepted=False)
            return {"outcome": "refused", "code": code}
        who = self.users.get_by_id(r.decided_by); name = who.email if who else cb.external_user
        key = "approved_by" if decision == "approved" else "rejected_by"
        a.acknowledge(sec, cb, text(mine, key, who=name), accepted=True)
        lang = self._lang(r.owner)  # the shared message: the owner's language, like the request
        self._update(a, sec, r, text(lang, "at", text=text(lang, key, who=name), when=time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())))
        return {"outcome": decision}

    def decide(self, kind, cid, token, external, team: str = "") -> tuple[Optional[str], Optional[ApprovalRequest], Optional[str]]:
        """Returns (refusal code, request, decision). Audits every attempt."""
        r, decision = self._parse(token)
        if r is None or r.channel_id != cid:
            log.warning("approval callback with an invalid token on channel %s", cid)
            return "APPROVAL_TOKEN_INVALID", None, None
        uid = self.repo.user_for(kind, external, team) if external else None  # verified in the workspace of the connection
        def refuse(code):
            self._audit(r.owner, kind, "denied", r, code=code, actor=uid, external=external); return code, r, None
        if r.status != "pending": return refuse("APPROVAL_ALREADY_DECIDED")
        if time.time() > r.expires:
            if self.repo.decide(r.id, "expired"): self._audit(r.owner, kind, "expired", r)
            return refuse("APPROVAL_TOKEN_EXPIRED")
        if uid is None: return refuse("APPROVAL_IDENTITY_UNKNOWN")
        return self._decide(r, decision, uid, kind, external)

    def _decide(self, r: ApprovalRequest, decision: str, uid: str, kind: str, external: Optional[str]) -> tuple[Optional[str], Optional[ApprovalRequest], Optional[str]]:
        """The checks after the presser is known: owner or listed approver, run still waiting, first answer wins."""
        def refuse(code):
            self._audit(r.owner, kind, "denied", r, code=code, actor=uid, external=external); return code, r, None
        if uid != r.owner and uid not in json.loads(r.approvers or "[]"): return refuse("APPROVAL_FORBIDDEN")
        run = self.runs.get(r.run_id)
        if run is None or run.status != "waiting" or not self.claim(r.run_id):
            self.repo.decide(r.id, "superseded"); return refuse("APPROVAL_ALREADY_DECIDED")
        if not self.repo.decide(r.id, decision, uid, external): return refuse("APPROVAL_ALREADY_DECIDED")  # lost the race: single use
        self._audit(r.owner, kind, decision, r, actor=uid, external=external)
        if self.enqueue: enqueue_resume(self.runs, self.enqueue, {"kind": "resume", "run_id": r.run_id, "owner": r.owner, "response": decision,
                                       "workflow_id": r.workflow_id, "approval_id": r.id, "by": {"channel": kind, "user_id": uid}})
        return None, self.repo.request(r.id), decision

    # ---- link channels: the studio's /approve page (TASK-0047) ----
    def _link(self, token: str) -> tuple[ApprovalRequest, str]:
        r, decision = self._parse(token)
        if r is None or r.kind not in self.adapters or not self.adapters[r.kind].link_based: raise AppError("APPROVAL_TOKEN_INVALID")
        return r, decision

    def link_info(self, token: str, uid: str) -> dict:
        """What the /approve page shows. Only the run owner and the listed approvers may see it."""
        r, decision = self._link(token)
        if uid != r.owner and uid not in json.loads(r.approvers or "[]"): raise AppError("APPROVAL_FORBIDDEN")
        w = self.workflows.get(r.workflow_id) if r.workflow_id else None; who = self.users.get_by_id(r.decided_by) if r.decided_by else None
        run = self.runs.get(r.run_id); events = json.loads(run.events or "[]") if run else []
        ev = next((e for e in reversed(events) if e.get("type") == "run_waiting"), {})
        return {"decision": decision, "status": r.status, "kind": r.kind, "workflow_id": r.workflow_id, "workflow_name": w.name if w else None,
                "run_id": r.run_id, "node": r.node_id, "label": ev.get("label"), "prompt": ev.get("prompt"), "expires": r.expires,
                "expired": r.status == "pending" and time.time() > r.expires,
                "decided_by": who.email if who else None}

    def decide_link(self, token: str, uid: str) -> dict:
        """The signed-in studio user confirms the link's decision. Refusals raise the APPROVAL_* code."""
        r, decision = self._link(token)
        if r.status != "pending": code, done = "APPROVAL_ALREADY_DECIDED", None
        elif time.time() > r.expires:
            if self.repo.decide(r.id, "expired"): self._audit(r.owner, r.kind, "expired", r)
            code, done = "APPROVAL_TOKEN_EXPIRED", None
        else: code, done, decision = self._decide(r, decision, uid, r.kind, None)
        if code:
            if code in ("APPROVAL_ALREADY_DECIDED", "APPROVAL_TOKEN_EXPIRED"): self._audit(r.owner, r.kind, "denied", r, code=code, actor=uid)
            raise AppError(code)
        who = self.users.get_by_id(uid); lang = self._lang(r.owner); key = "approved_by" if decision == "approved" else "rejected_by"
        c = self.repo.channel(r.channel_id)
        if c is not None:
            note = lambda: self._update(self.adapters[r.kind], self._secrets(c), done, text(lang, "at", text=text(lang, key, who=who.email if who else uid),  # noqa: E731
                                                                                   when=time.strftime("%Y-%m-%d %H:%M UTC", time.gmtime())))
            threading.Thread(target=note, daemon=True).start() if self.background else note()
        return {"decision": decision, "run_id": r.run_id, "workflow_id": r.workflow_id}

    def _update(self, a: ApprovalChannel, sec: dict, r: ApprovalRequest, text: str) -> None:
        if not r.message_ref: return
        try: a.update(sec, json.loads(r.message_ref), text)
        except AppError as e: log.warning("updating the approval message of run %s failed: %s", r.run_id, e.message)

    # ---- the Approvals inbox (TASK-0065) ----
    def answered_in_studio(self, w: ApprovalWait, uid: str, response: str) -> None:
        """An inbox answer whose waiting step the caller already closed: close the channel requests, audit it and resume
        the run like a channel decision (the run stays its owner's)."""
        self.close_run(w.run_id, "answered")
        self._audit(w.owner, "studio", response if response in DECISIONS.values() else "answered", actor=uid, run_id=w.run_id, wid=w.workflow_id)
        if self.enqueue: enqueue_resume(self.runs, self.enqueue, {"kind": "resume", "run_id": w.run_id, "owner": w.owner, "response": response, "workflow_id": w.workflow_id,
                                       "by": {"channel": "studio", "user_id": uid}})

    # ---- the run went on without the channel (answered in the studio, cancelled, expired) ----
    def decided_elsewhere(self, rid: str) -> bool:
        """True when a channel decision for this run is already queued (the studio must not resume it a second time)."""
        return any(r.status in DECISIONS.values() for r in self.repo.requests_for_run(rid)) and \
            (run := self.runs.get(rid)) is not None and run.status == "waiting"

    def close_run(self, rid: str, reason: str) -> int:
        """Mark open requests of the run superseded/expired now (compare-and-set, so a late button press is refused) and
        edit their messages in the background. reason: answered | cancelled | expired | finished | deadline_approved |
        deadline_rejected. The waiting step closes too."""
        self.repo.close_wait(rid, reason)
        return self._close_requests(rid, "expired" if reason == "expired" else "superseded", reason if reason in CLOSE_TEXTS else "finished")

    def _close_requests(self, rid: str, action: str, key: str) -> int:
        """Close the run's pending channel requests and edit their messages to `key` (a chat text)."""
        closed = []
        for r in self.repo.requests_for_run(rid, "pending"):
            if self.repo.decide(r.id, action): closed.append(r); self._audit(r.owner, r.kind, action, r)
        if closed:
            def edit():
                for r in closed:
                    c = self.repo.channel(r.channel_id)
                    if c is not None and r.kind in self.adapters: self._update(self.adapters[r.kind], self._secrets(c), r, text(self._lang(r.owner), key))
            threading.Thread(target=edit, daemon=True).start() if self.background else edit()
        return len(closed)

    # ---- deadlines (TASK-0066): fired by the worker's maintenance loop ----
    def fire_deadlines(self, now: Optional[float] = None) -> int:
        """Send due reminders and act on due deadlines. Each one is claimed with a compare-and-set, so it fires once with
        several workers and after a restart (a deadline missed during downtime fires on the first sweep). Returns how many fired."""
        now = time.time() if now is None else now; fired = 0
        for w in self.repo.due_waits(now):
            try:
                if w.due_at is not None and w.due_at <= now: fired += self._timeout(w, now)
                elif w.next_remind_at is not None and w.next_remind_at <= now: fired += self._remind(w, now)
            except Exception: log.exception("deadline of run %s failed", w.run_id)
        return fired

    def _remind(self, w: ApprovalWait, now: float) -> int:
        dl = json.loads(w.deadline or "{}"); every = dl.get("remind_every"); count = (w.reminders or 0) + 1
        nxt = now + every if every and count < deadlines.MAX_REMINDERS and now + every < (w.due_at or float("inf")) else None
        if not self.repo.claim_reminder(w.id, w.next_remind_at, nxt, count): return 0
        self._audit(w.owner, w.channel or "studio", "reminded", run_id=w.run_id, wid=w.workflow_id)
        self._reach(w, "run_reminder", [w.owner, *self.repo.wait_approvers(w.id)], "reminded")
        return 1

    def _timeout(self, w: ApprovalWait, now: float) -> int:
        dl = json.loads(w.deadline or "{}"); action = dl.get("on_timeout") or "reject"
        kind = w.channel or "studio"; skipped: list[str] = []
        def log_skipped():  # only by the sweep that won the step, so two sweeps do not log twice
            for e in skipped: self._audit(w.owner, kind, "escalation_skipped", run_id=w.run_id, wid=w.workflow_id, external=e)
        if action == "escalate" and w.escalated_at is None:
            ids = []
            for e in dl.get("escalate_to") or []:
                u = self.users.get_by_email(e)
                if u is not None: ids.append(u.id)
                else: skipped.append(e)
            if ids:
                every = dl.get("remind_every")
                if not self.repo.escalate_wait(w.id, w.due_at, now + dl["after"], now + every if every else None, ids, now): return 0
                log_skipped(); self._audit(w.owner, kind, "escalated", run_id=w.run_id, wid=w.workflow_id)
                self._reach(w, "run_escalated", ids, "escalated", extra=dl.get("escalate_to") or [], due=now + dl["after"])
                return 1
        response = deadlines.RESPONSES.get(action, "rejected")  # a second deadline after an escalation rejects
        if not self.repo.close_wait(w.run_id, "deadline", w.id): return 0  # this step only: the run may wait at a later one by now
        log_skipped()
        self.close_run(w.run_id, f"deadline_{response}")
        self._audit(w.owner, kind, "timed_out", run_id=w.run_id, wid=w.workflow_id)
        if self.enqueue: enqueue_resume(self.runs, self.enqueue, {"kind": "resume", "run_id": w.run_id, "owner": w.owner, "response": response, "workflow_id": w.workflow_id,
                                       "by": {"channel": "deadline", "on_timeout": action}})
        return 1

    def _reach(self, w: ApprovalWait, kind: str, uids: list[str], key: str, extra: list[str] = (), due: Optional[float] = None) -> None:
        """A reminder or an escalation: a notification to `uids` and, on a channel node, a new request message that
        replaces the open one (its buttons stop working)."""
        ev = {"node": w.node_id, "label": w.label, "prompt": w.prompt}
        if self.notifier is not None:
            for uid in dict.fromkeys(uids):
                try: self.notifier.run_event(kind, uid, w.run_id, w.workflow_id, ev, link="/approvals")
                except Exception: log.exception("deadline notification for run %s failed", w.run_id)
        if not w.approval: return
        cfg = json.loads(w.approval); cfg = {**cfg, "approvers": [*(cfg.get("approvers") or []), *extra]}
        def send():
            self._close_requests(w.run_id, "superseded", key)
            self._request(w.run_id, w.owner, w.workflow_id, {"id": w.node_id}, cfg, str(cfg.get("target") or "").strip(), ev, due or w.due_at)
        threading.Thread(target=send, daemon=True).start() if self.background else send()
