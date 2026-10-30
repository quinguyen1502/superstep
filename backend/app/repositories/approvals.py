import json, time, uuid
from typing import Optional
from sqlalchemy import delete, func, or_, select, update
from ..models import ApprovalAudit, ApprovalChannel, ApprovalRequest, ApprovalWait, ApprovalWaitApprover, ChannelIdentity, Run
from ..models.database import Database


class ApprovalRepository:
    """Channels, identities, approval requests and their audit log (TASK-0022)."""
    def __init__(self, db: Database): self.db = db

    # ---- channels ----
    def channels_visible(self, uid: str) -> list[ApprovalChannel]:
        """The user's own channels plus every org-wide channel."""
        with self.db.session() as s:
            q = select(ApprovalChannel).where(or_(ApprovalChannel.owner == uid, ApprovalChannel.scope == "org"))
            return list(s.scalars(q.order_by(ApprovalChannel.scope.desc(), ApprovalChannel.kind, ApprovalChannel.created)))

    def channel(self, cid: str) -> Optional[ApprovalChannel]:
        with self.db.session() as s: return s.get(ApprovalChannel, cid)

    def find_channel(self, owner: str, kind: str, scope: str, team_id: Optional[str] = None, any_team: bool = True) -> Optional[ApprovalChannel]:
        """The owner's oldest connection of this kind and scope; with any_team=False only the one for this account."""
        with self.db.session() as s:
            q = select(ApprovalChannel).where(ApprovalChannel.owner == owner, ApprovalChannel.kind == kind, ApprovalChannel.scope == scope)
            if not any_team: q = q.where(ApprovalChannel.team_id == team_id if team_id else ApprovalChannel.team_id.is_(None))
            return s.scalars(q.order_by(ApprovalChannel.created)).first()

    def channels_by_team(self, kind: str, team_id: str) -> list[ApprovalChannel]:
        with self.db.session() as s:
            return list(s.scalars(select(ApprovalChannel).where(ApprovalChannel.kind == kind, ApprovalChannel.team_id == team_id).order_by(ApprovalChannel.created)))

    def org_channel(self, kind: str) -> Optional[ApprovalChannel]:
        with self.db.session() as s:
            return s.scalars(select(ApprovalChannel).where(ApprovalChannel.kind == kind, ApprovalChannel.scope == "org").order_by(ApprovalChannel.created)).first()

    def save_channel(self, row: ApprovalChannel) -> ApprovalChannel:
        """Insert, or update the row with this id (the id, and so the callback URL, stays the same)."""
        with self.db.session() as s: row = s.merge(row); s.commit(); s.refresh(row); return row

    def delete_channel(self, cid: str) -> int:
        with self.db.session() as s:
            n = s.execute(delete(ApprovalChannel).where(ApprovalChannel.id == cid)).rowcount; s.commit(); return n or 0

    @staticmethod
    def new_id() -> str: return uuid.uuid4().hex[:12]

    # ---- identities (key: user, kind, team_id; team_id "" for platforms without workspaces) ----
    def identities(self, uid: str) -> list[ChannelIdentity]:
        with self.db.session() as s:
            return list(s.scalars(select(ChannelIdentity).where(ChannelIdentity.user_id == uid).order_by(ChannelIdentity.kind, ChannelIdentity.team_id)))

    def identity(self, uid: str, kind: str, team: str = "") -> Optional[ChannelIdentity]:
        with self.db.session() as s: return s.get(ChannelIdentity, (uid, kind, team))

    def user_for(self, kind: str, external_id: str, team: str = "") -> Optional[str]:
        """The studio user with a *verified* link to this account in this workspace (None when nobody proved it)."""
        with self.db.session() as s:
            return s.scalar(select(ChannelIdentity.user_id).where(ChannelIdentity.kind == kind, ChannelIdentity.team_id == team,
                                                                  ChannelIdentity.external_id == external_id, ChannelIdentity.verified_at.is_not(None)))

    def linked(self, kind: str, external_id: str, team: str = "") -> bool:
        """Someone linked this account, verified or not (chat triggers tell "not linked" from "not verified", TASK-0075)."""
        with self.db.session() as s:
            return s.scalar(select(ChannelIdentity.user_id).where(ChannelIdentity.kind == kind, ChannelIdentity.team_id == team,
                                                                  ChannelIdentity.external_id == external_id).limit(1)) is not None

    def put_identity(self, uid: str, kind: str, team: str, external_id: Optional[str]) -> None:
        """Link (unverified, no code yet) or unlink with None. Relinking the same account keeps its state."""
        with self.db.session() as s:
            row = s.get(ChannelIdentity, (uid, kind, team))
            if row is not None and row.external_id == external_id: return
            if row is not None: s.delete(row); s.flush()
            if external_id: s.add(ChannelIdentity(user_id=uid, kind=kind, team_id=team, external_id=external_id, created=time.time(), code_attempts=0))
            s.commit()

    @staticmethod
    def _key(uid: str, kind: str, team: str):
        return (ChannelIdentity.user_id == uid, ChannelIdentity.kind == kind, ChannelIdentity.team_id == team)

    def set_identity(self, uid: str, kind: str, team: str = "", **vals) -> None:
        with self.db.session() as s: s.execute(update(ChannelIdentity).where(*self._key(uid, kind, team)).values(**vals)); s.commit()

    def verify_identity(self, uid: str, kind: str, team: str, at: float) -> bool:
        """Mark verified in one transaction; False if another user verified the same account first (unique index)."""
        from sqlalchemy.exc import IntegrityError
        with self.db.session() as s:
            try:
                s.execute(update(ChannelIdentity).where(*self._key(uid, kind, team))
                          .values(verified_at=at, code_hash=None, code_expires=None, code_attempts=0)); s.commit(); return True
            except IntegrityError: s.rollback(); return False

    def count_attempt(self, uid: str, kind: str, team: str = "") -> int:
        """Atomically count a wrong code; returns the new count."""
        with self.db.session() as s:
            s.execute(update(ChannelIdentity).where(*self._key(uid, kind, team)).values(code_attempts=ChannelIdentity.code_attempts + 1)); s.commit()
            return s.scalar(select(ChannelIdentity.code_attempts).where(*self._key(uid, kind, team))) or 0

    # ---- requests ----
    def add_request(self, r: ApprovalRequest) -> ApprovalRequest:
        with self.db.session() as s: s.add(r); s.commit(); return r

    def request(self, aid: str) -> Optional[ApprovalRequest]:
        with self.db.session() as s: return s.get(ApprovalRequest, aid)

    def requests_for_run(self, rid: str, status: Optional[str] = None) -> list[ApprovalRequest]:
        with self.db.session() as s:
            q = select(ApprovalRequest).where(ApprovalRequest.run_id == rid)
            if status: q = q.where(ApprovalRequest.status == status)
            return list(s.scalars(q))

    def set_ref(self, aid: str, ref: Optional[dict], status: Optional[str] = None) -> None:
        with self.db.session() as s:
            vals = {"message_ref": json.dumps(ref) if ref is not None else None, **({"status": status} if status else {})}
            s.execute(update(ApprovalRequest).where(ApprovalRequest.id == aid).values(**vals)); s.commit()

    def decide(self, aid: str, status: str, by: Optional[str] = None, external: Optional[str] = None) -> bool:
        """Compare-and-set pending -> status. Exactly one caller wins (single-use tokens)."""
        with self.db.session() as s:
            n = s.execute(update(ApprovalRequest).where(ApprovalRequest.id == aid, ApprovalRequest.status == "pending")
                          .values(status=status, decided_by=by, decided_external=external, decided_at=time.time())).rowcount
            s.commit(); return n == 1

    # ---- waiting steps (TASK-0065, DEC-0043) ----
    def add_wait(self, w: ApprovalWait, approvers: list[str]) -> ApprovalWait:
        """A new pause at this node. An older open wait of the same node is closed. Other nodes of the run keep theirs."""
        with self.db.session() as s:
            s.execute(update(ApprovalWait).where(ApprovalWait.run_id == w.run_id, ApprovalWait.node_id == w.node_id,
                                                 ApprovalWait.status == "waiting")
                      .values(status="closed", outcome="superseded", closed_at=time.time()))
            s.add(w); s.add_all(ApprovalWaitApprover(wait_id=w.id, user_id=u) for u in dict.fromkeys(approvers) if u != w.owner)
            s.commit(); return w

    def open_wait(self, rid: str, node: str) -> Optional[ApprovalWait]:
        """The open waiting step of this node, if the run still has one."""
        with self.db.session() as s:
            return s.scalars(select(ApprovalWait).where(ApprovalWait.run_id == rid, ApprovalWait.node_id == node,
                                                       ApprovalWait.status == "waiting")).first()

    def latest_wait(self, rid: str) -> Optional[ApprovalWait]:
        """The run's most recent waiting step, open or closed."""
        with self.db.session() as s:
            return s.scalars(select(ApprovalWait).where(ApprovalWait.run_id == rid).order_by(ApprovalWait.created.desc())).first()

    def wait_approvers(self, wid: str) -> list[str]:
        with self.db.session() as s: return list(s.scalars(select(ApprovalWaitApprover.user_id).where(ApprovalWaitApprover.wait_id == wid)))

    def close_wait(self, rid: str, outcome: str, wid: Optional[str] = None) -> bool:
        """Compare-and-set the run's open step waiting -> closed. Exactly one caller wins. wid: only that step (a deadline
        must not close a later step of the same run)."""
        with self.db.session() as s:
            q = update(ApprovalWait).where(ApprovalWait.run_id == rid, ApprovalWait.status == "waiting")
            n = s.execute((q.where(ApprovalWait.id == wid) if wid else q)
                          .values(status="closed", outcome=outcome, closed_at=time.time())).rowcount
            s.commit(); return n == 1

    def due_waits(self, now: float, limit: int = 200) -> list[ApprovalWait]:
        """Open steps of waiting runs whose deadline or next reminder has come (TASK-0066)."""
        with self.db.session() as s:
            q = (select(ApprovalWait).join(Run, Run.id == ApprovalWait.run_id)
                 .where(ApprovalWait.status == "waiting", Run.status == "waiting", or_(ApprovalWait.due_at <= now, ApprovalWait.next_remind_at <= now)))
            return list(s.scalars(q.order_by(ApprovalWait.created).limit(limit)))

    def claim_reminder(self, wid: str, expected: float, nxt: Optional[float], count: int) -> bool:
        """Compare-and-set on the step's next reminder time: one sweep sends it, however many workers run."""
        with self.db.session() as s:
            n = s.execute(update(ApprovalWait).where(ApprovalWait.id == wid, ApprovalWait.status == "waiting", ApprovalWait.next_remind_at == expected)
                          .values(next_remind_at=nxt, reminders=count)).rowcount
            s.commit(); return n == 1

    def escalate_wait(self, wid: str, expected_due: float, due: float, nxt: Optional[float], approvers: list[str], now: float) -> bool:
        """Compare-and-set the one escalation of a step, adding the new approvers in the same transaction."""
        with self.db.session() as s:
            n = s.execute(update(ApprovalWait).where(ApprovalWait.id == wid, ApprovalWait.status == "waiting", ApprovalWait.escalated_at.is_(None),
                                                     ApprovalWait.due_at == expected_due)
                          .values(escalated_at=now, due_at=due, next_remind_at=nxt, reminders=0)).rowcount
            if n == 1:
                have = set(s.scalars(select(ApprovalWaitApprover.user_id).where(ApprovalWaitApprover.wait_id == wid)))
                s.add_all(ApprovalWaitApprover(wait_id=wid, user_id=u) for u in dict.fromkeys(approvers) if u not in have)
            s.commit(); return n == 1

    def inbox(self, uid: str, limit: int = 200) -> list[ApprovalWait]:
        """Open steps of runs still waiting that the user owns or may answer: nearest deadline first, then the longest waiting."""
        with self.db.session() as s:
            mine = select(ApprovalWaitApprover.wait_id).where(ApprovalWaitApprover.user_id == uid)
            q = (select(ApprovalWait).join(Run, Run.id == ApprovalWait.run_id)
                 .where(ApprovalWait.status == "waiting", Run.status == "waiting", or_(ApprovalWait.owner == uid, ApprovalWait.id.in_(mine))))
            return list(s.scalars(q.order_by(ApprovalWait.due_at.is_(None), ApprovalWait.due_at, ApprovalWait.created).limit(limit)))

    def set_opinion(self, wid: str, decision: Optional[str], confidence: Optional[float], reason: Optional[str]) -> None:
        """The AI's opinion on a waiting step (TASK-0187), shown to the people who answer it."""
        with self.db.session() as s:
            s.execute(update(ApprovalWait).where(ApprovalWait.id == wid).values(ai_decision=decision, ai_confidence=confidence, ai_reason=reason))
            s.commit()

    def wait_of(self, wid: str) -> Optional[ApprovalWait]:
        with self.db.session() as s: return s.get(ApprovalWait, wid)

    def count_auto(self, workflow_id: str, since: float) -> int:
        """Automatic answers (approved or rejected by AI review) of a workflow since `since` (the daily cap)."""
        with self.db.session() as s:
            return s.scalar(select(func.count()).select_from(ApprovalAudit).where(
                ApprovalAudit.workflow_id == workflow_id, ApprovalAudit.created >= since, ApprovalAudit.kind == "auto",
                ApprovalAudit.auto_outcome.in_(("approved", "rejected")))) or 0

    def auto_stats(self, workflow_id: str, since: float) -> dict:
        """{approved, rejected, escalated, suggested, agreed, disagreed} of a workflow since `since`."""
        with self.db.session() as s:
            base = (ApprovalAudit.workflow_id == workflow_id, ApprovalAudit.created >= since)
            out = {k: n for k, n in s.execute(select(ApprovalAudit.auto_outcome, func.count()).where(
                *base, ApprovalAudit.kind == "auto", ApprovalAudit.auto_outcome.is_not(None)).group_by(ApprovalAudit.auto_outcome))}
            for v, n in s.execute(select(ApprovalAudit.agreed, func.count()).where(*base, ApprovalAudit.agreed.is_not(None)).group_by(ApprovalAudit.agreed)):
                out["agreed" if v else "disagreed"] = n
            return out

    # ---- audit ----
    def audit(self, e: ApprovalAudit) -> None:
        with self.db.session() as s: s.add(e); s.commit()

    def audit_for(self, owner: str, limit: int = 100) -> list[ApprovalAudit]:
        with self.db.session() as s:
            return list(s.scalars(select(ApprovalAudit).where(ApprovalAudit.owner == owner).order_by(ApprovalAudit.created.desc()).limit(limit)))
