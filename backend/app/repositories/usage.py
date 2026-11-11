"""Aggregates for the admin Usage page and the product health gauges. SQL aggregation only (SQLite and Postgres);
the JSON `runs.events` column is never read. Top-level runs only: a workflow tool's child run is part of its
parent, whose node usage already includes the child's tokens and cost."""
from typing import Optional
from sqlalchemy import BigInteger, and_, case, cast, func, select
from ..models import Run
from ..models.approval import ApprovalWait
from ..models.chat_message import ChatMessage
from ..models.run_usage import RunUsage
from ..models.team import Team, TeamMember
from ..models.user import User
from ..models.browser_session import BrowserSession
from ..models.database import Database
from ..models.webhook_delivery import WebhookDelivery
from ..models.workflow import Workflow
from ..models.workflow_schedule import WorkflowSchedule

FINISHED = ("ok", "error", "timeout", "cancelled")


class UsageRepository:
    def __init__(self, db: Database): self.db = db

    @staticmethod
    def _window(since: float, until: float):
        return (Run.started >= since, Run.started < until, Run.parent_run_id.is_(None))

    def totals(self, since: float, until: float) -> dict:
        """Runs by status, token sums, cost of priced runs and the count of finished runs with no price."""
        unpriced = func.sum(case((and_(Run.status.in_(FINISHED), Run.cost_usd.is_(None)), 1), else_=0))
        with self.db.session() as s:
            rows = s.execute(select(Run.status, func.count(), func.coalesce(func.sum(Run.tokens_in), 0), func.coalesce(func.sum(Run.tokens_out), 0),
                                    func.coalesce(func.sum(Run.cost_usd), 0.0), func.coalesce(unpriced, 0))
                             .where(*self._window(since, until)).group_by(Run.status)).all()
        out = {"by_status": {}, "tokens_in": 0, "tokens_out": 0, "cost_usd": 0.0, "unpriced_runs": 0}
        for status, n, tin, tout, cost, unp in rows:
            out["by_status"][status or "unknown"] = int(n); out["tokens_in"] += int(tin); out["tokens_out"] += int(tout)
            out["cost_usd"] += float(cost); out["unpriced_runs"] += int(unp)
        return out

    def series(self, since: float, until: float, size: int) -> list[tuple[int, str, int]]:
        """(bucket index, status, runs): bucket i covers [since + i*size, since + (i+1)*size). Integer division of
        non-negative integers floors on both SQLite and Postgres."""
        bucket = (cast(Run.started, BigInteger) - int(since)) / size
        with self.db.session() as s:
            rows = s.execute(select(bucket, Run.status, func.count()).where(*self._window(since, until)).group_by(bucket, Run.status)).all()
        return [(int(b), st or "unknown", int(n)) for b, st, n in rows]

    def top_workflows(self, since: float, until: float, limit: int = 10, by: str = "runs") -> list[dict]:
        errors = func.sum(case((Run.status.in_(("error", "timeout")), 1), else_=0))
        unpriced = func.sum(case((and_(Run.status.in_(FINISHED), Run.cost_usd.is_(None)), 1), else_=0))
        cost = func.coalesce(func.sum(Run.cost_usd), 0.0); runs = func.count()
        q = (select(Run.workflow_id, runs, errors, func.coalesce(func.sum(Run.tokens_in), 0), func.coalesce(func.sum(Run.tokens_out), 0), cost, unpriced)
             .where(*self._window(since, until)).group_by(Run.workflow_id)
             .order_by((cost if by == "cost" else runs).desc(), Run.workflow_id).limit(limit))
        with self.db.session() as s:
            rows = s.execute(q).all()
            ids = [r[0] for r in rows if r[0]]
            names = dict(s.execute(select(Workflow.id, Workflow.name).where(Workflow.id.in_(ids))).all()) if ids else {}
        return [{"workflow_id": wid, "name": names.get(wid), "runs": int(n), "errors": int(e or 0), "tokens_in": int(tin), "tokens_out": int(tout),
                 "cost_usd": float(c), "unpriced_runs": int(u or 0)} for wid, n, e, tin, tout, c, u in rows]

    # ---- per model, user and team (SQL only; never metric labels) ----
    def models(self, since: float, until: float, limit: int = 50) -> list[dict]:
        """Usage rows of runs that ended in the window, by kind, model and provider (child runs included: each run
        writes only its own calls). `unpriced_rows`: rows whose model has no price (cost unknown)."""
        cost = func.coalesce(func.sum(RunUsage.cost_usd), 0.0)
        unpriced = func.sum(case((RunUsage.cost_usd.is_(None), 1), else_=0))
        q = (select(RunUsage.kind, RunUsage.model, RunUsage.provider, func.count(func.distinct(RunUsage.run_id)), func.sum(RunUsage.calls),
                    func.sum(RunUsage.errors), func.sum(RunUsage.tokens_in), func.sum(RunUsage.tokens_out), cost, unpriced, func.sum(RunUsage.duration_ms))
             .where(RunUsage.created >= since, RunUsage.created < until).group_by(RunUsage.kind, RunUsage.model, RunUsage.provider)
             .order_by(cost.desc(), RunUsage.model).limit(limit))
        with self.db.session() as s: rows = s.execute(q).all()
        return [{"kind": k, "model": m, "provider": p, "runs": int(n), "calls": int(c or 0), "errors": int(e or 0), "tokens_in": int(tin or 0),
                 "tokens_out": int(tout or 0), "cost_usd": float(cs), "unpriced_rows": int(u or 0),
                 "avg_duration_ms": round(float(d or 0) / int(c), 2) if c else None} for k, m, p, n, c, e, tin, tout, cs, u, d in rows]

    def usage_since(self) -> Optional[float]:
        """When per-model data starts: the oldest usage row (migration or backfill), None before any."""
        with self.db.session() as s: return s.scalar(select(func.min(RunUsage.created)))

    def _per(self, key, since: float, until: float, by: str, limit: int, join=None) -> list[tuple]:
        unpriced = func.sum(case((and_(Run.status.in_(FINISHED), Run.cost_usd.is_(None)), 1), else_=0))
        cost = func.coalesce(func.sum(Run.cost_usd), 0.0); runs = func.count()
        q = select(key, runs, func.coalesce(func.sum(Run.tokens_in), 0), func.coalesce(func.sum(Run.tokens_out), 0), cost, func.coalesce(unpriced, 0))
        if join is not None: q = q.join(*join)
        q = q.where(*self._window(since, until)).group_by(key).order_by((cost if by == "cost" else runs).desc(), key).limit(limit)
        with self.db.session() as s: return s.execute(q).all()

    def users(self, since: float, until: float, by: str = "runs", limit: int = 20) -> list[dict]:
        """Top-level runs by owner; `email` None when the user is gone (deleted or anonymised)."""
        rows = self._per(Run.owner, since, until, by, limit)
        ids = [r[0] for r in rows if r[0]]
        with self.db.session() as s:
            emails = dict(s.execute(select(User.id, User.email).where(User.id.in_(ids))).all()) if ids else {}
        return [{"user_id": uid, "email": emails.get(uid), "runs": int(n), "tokens_in": int(tin), "tokens_out": int(tout), "cost_usd": float(c),
                 "unpriced_runs": int(u)} for uid, n, tin, tout, c, u in rows]

    def teams(self, since: float, until: float, by: str = "runs", limit: int = 20) -> list[dict]:
        """Top-level runs of each team's members (a member of two teams counts toward both)."""
        rows = self._per(TeamMember.team_id, since, until, by, limit, join=(TeamMember, TeamMember.user_id == Run.owner))
        ids = [r[0] for r in rows]
        with self.db.session() as s:
            names = dict(s.execute(select(Team.id, Team.name).where(Team.id.in_(ids))).all()) if ids else {}
            members = dict(s.execute(select(TeamMember.team_id, func.count()).where(TeamMember.team_id.in_(ids)).group_by(TeamMember.team_id)).all()) if ids else {}
        return [{"team_id": tid, "name": names.get(tid), "members": int(members.get(tid, 0)), "runs": int(n), "tokens_in": int(tin),
                 "tokens_out": int(tout), "cost_usd": float(c), "unpriced_runs": int(u)} for tid, n, tin, tout, c, u in rows]

    def shared_members(self, since: float, until: float) -> int:
        """Users with runs in the window who belong to more than one team (their usage appears in each)."""
        multi = select(TeamMember.user_id).group_by(TeamMember.user_id).having(func.count() > 1)
        with self.db.session() as s:
            return int(s.scalar(select(func.count(func.distinct(Run.owner))).where(*self._window(since, until), Run.owner.in_(multi))) or 0)

    # ---- chat triggers ----
    def chat_refusals(self, since: float, until: float) -> dict:
        """Chat trigger messages refused in the window by code and platform, and the messages that started a run."""
        window = (ChatMessage.created >= since, ChatMessage.created < until)
        with self.db.session() as s:
            rows = s.execute(select(ChatMessage.code, ChatMessage.kind, func.count()).where(ChatMessage.status == "refused", *window)
                             .group_by(ChatMessage.code, ChatMessage.kind).order_by(func.count().desc(), ChatMessage.code)).all()
            started = s.scalar(select(func.count()).where(ChatMessage.status == "started", *window))
        return {"refused": [{"code": c or "unknown", "kind": k, "count": int(n)} for c, k, n in rows], "started": int(started or 0)}

    # ---- product health ----
    def approvals(self, since: float) -> dict:
        with self.db.session() as s:
            waiting, oldest = s.execute(select(func.count(), func.min(ApprovalWait.created)).where(ApprovalWait.status == "waiting")).one()
            expired = s.scalar(select(func.count()).where(ApprovalWait.status == "closed", ApprovalWait.outcome == "expired",
                                                          ApprovalWait.closed_at >= since))
        return {"waiting": int(waiting or 0), "oldest_created": oldest, "expired": int(expired or 0)}

    def active_browsers(self, now: float) -> int:
        with self.db.session() as s:
            return int(s.scalar(select(func.count()).where(BrowserSession.status.in_(("new", "starting", "ready", "renewing")),
                                                           BrowserSession.expires > now)) or 0)

    def webhooks(self, since: float) -> dict:
        with self.db.session() as s:
            failed = s.scalar(select(func.count()).where(WebhookDelivery.status == "failed", func.coalesce(WebhookDelivery.updated, WebhookDelivery.created) >= since))
            retrying = s.scalar(select(func.count()).where(WebhookDelivery.status == "retrying"))
        return {"failed": int(failed or 0), "retrying": int(retrying or 0)}

    def schedules(self, overdue_before: float, limit: int = 20) -> dict:
        with self.db.session() as s:
            overdue = s.scalar(select(func.count()).where(WorkflowSchedule.enabled.is_(True), WorkflowSchedule.next_run < overdue_before))
            stopped = WorkflowSchedule.enabled.is_(False) & WorkflowSchedule.note.is_not(None)
            disabled = s.scalar(select(func.count()).where(stopped))
            rows = s.execute(select(WorkflowSchedule.id, WorkflowSchedule.workflow_id, WorkflowSchedule.name, WorkflowSchedule.note)
                             .where(stopped).order_by(WorkflowSchedule.created.desc()).limit(limit)).all()
        return {"overdue": int(overdue or 0), "disabled": int(disabled or 0),
                "disabled_list": [{"id": i, "workflow_id": w, "name": n, "note": note} for i, w, n, note in rows]}

