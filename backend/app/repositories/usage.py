"""Aggregates for the admin Usage page and the product health gauges. SQL aggregation only (SQLite and Postgres);
the JSON `runs.events` column is never read. Top-level runs only: a workflow tool's child run is part of its
parent, whose node usage already includes the child's tokens and cost."""
from sqlalchemy import BigInteger, and_, case, cast, func, select
from ..models import Run
from ..models.approval import ApprovalWait
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

    # ---- product health ----
    def approvals(self, since: float) -> dict:
        with self.db.session() as s:
            waiting, oldest = s.execute(select(func.count(), func.min(ApprovalWait.created)).where(ApprovalWait.status == "waiting")).one()
            expired = s.scalar(select(func.count()).where(ApprovalWait.status == "closed", ApprovalWait.outcome == "expired",
                                                          ApprovalWait.closed_at >= since))
        return {"waiting": int(waiting or 0), "oldest_created": oldest, "expired": int(expired or 0)}

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

