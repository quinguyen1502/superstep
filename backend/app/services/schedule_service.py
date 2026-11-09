"""Scheduled runs: cron schedules per workflow, fired by the run worker.

Managing schedules needs the workflow's "share" right (owner or admin), like API tokens: a schedule spends the owner's
credentials with nobody watching. A run starts as the schedule's creator with `source="schedule"` and goes through the same
job queue as API runs. Missed times while no worker ran are not replayed: a due schedule fires once and moves to its next time.
"""
import json, time, uuid
from typing import List, Optional
from ..core import config, permissions as P
from ..core.errors import AppError
from ..core.logging import get_logger
from ..engine.limits import size
from ..models import Run, WorkflowSchedule
from ..repositories import RunRepository, ScheduleRepository, WorkflowRepository
from . import cron
from .job_queue import JobQueue

log = get_logger("schedules")
MAX_PER_WORKFLOW = 20


def _cron_error(e: cron.CronError) -> AppError: return AppError("SCHEDULE_CRON_INVALID", reason=str(e))


def check(expr: str, tz: str) -> tuple[cron.Cron, object]:
    try: return cron.parse(expr), cron.zone(tz)
    except cron.CronError as e: raise _cron_error(e)


class ScheduleService:
    def __init__(self, schedules: ScheduleRepository, workflows: WorkflowRepository, runs: RunRepository, jobs: JobQueue, access=None):
        self.schedules, self.workflows, self.runs, self.jobs, self.access = schedules, workflows, runs, jobs, access

    def _manage(self, wid: str, uid: str) -> None:
        if self.access is not None: self.access.workflow(wid, uid, P.SHARE); return
        if self.workflows.get_owned(wid, uid) is None: raise AppError("WORKFLOW_NOT_FOUND")

    def _own(self, wid: str, sid: str, uid: str) -> WorkflowSchedule:
        self._manage(wid, uid); s = self.schedules.get(sid)
        if s is None or s.workflow_id != wid: raise AppError("SCHEDULE_NOT_FOUND")
        return s

    @staticmethod
    def public(s: WorkflowSchedule) -> dict:
        upcoming = cron.upcoming(s.cron, s.timezone, time.time(), 3) if s.enabled else []
        return {"id": s.id, "name": s.name, "cron": s.cron, "timezone": s.timezone, "input": json.loads(s.input or "{}"), "enabled": s.enabled,
                "next_runs": upcoming, "last_run": s.last_run, "last_run_id": s.last_run_id, "note": s.note, "created": s.created}

    @staticmethod
    def _input(inp) -> str:
        if not isinstance(inp, dict): raise AppError("RUN_INPUT_INVALID")
        if size(inp) > config.input_max(): raise AppError("RUN_INPUT_TOO_LARGE", max_kb=config.input_max() // 1024)
        return json.dumps(inp, ensure_ascii=False)

    def _next(self, expr: str, tz: str, after: float) -> Optional[float]:
        c, z = check(expr, tz); return cron.next_time(c, z, after)

    # ---- owner API ----
    def list(self, wid: str, uid: str) -> list[dict]:
        self._manage(wid, uid); return [self.public(s) for s in self.schedules.list_for_workflow(wid)]

    def create(self, wid: str, uid: str, name: str, expr: str, tz: str, inp: dict, enabled: bool = True) -> dict:
        self._manage(wid, uid)
        if self.schedules.count_for_workflow(wid) >= MAX_PER_WORKFLOW: raise AppError("SCHEDULE_LIMIT", max=MAX_PER_WORKFLOW)
        nxt = self._next(expr, tz, time.time())
        s = self.schedules.add(WorkflowSchedule(id=uuid.uuid4().hex[:10], workflow_id=wid, owner=uid, name=(name or "Schedule").strip()[:80] or "Schedule",
                                                cron=expr.strip(), timezone=tz, input=self._input(inp), enabled=enabled,
                                                next_run=nxt if enabled else None, created=time.time()))
        return self.public(s)

    def update(self, wid: str, sid: str, uid: str, **patch) -> dict:
        s = self._own(wid, sid, uid); vals = {k: v for k, v in patch.items() if v is not None}
        if "name" in vals: vals["name"] = vals["name"].strip()[:80] or s.name
        if "cron" in vals: vals["cron"] = vals["cron"].strip()
        if "input" in vals: vals["input"] = self._input(vals["input"])
        expr, tz, on = vals.get("cron", s.cron), vals.get("timezone", s.timezone), vals.get("enabled", s.enabled)
        vals["next_run"] = self._next(expr, tz, time.time()) if on else None
        if on: vals["note"] = None
        self.schedules.set_fields(sid, **vals)
        return self.public(self.schedules.get(sid))

    def delete(self, wid: str, sid: str, uid: str) -> dict:
        self._own(wid, sid, uid); self.schedules.delete(sid); return {"ok": True}

    @staticmethod
    def preview(expr: str, tz: str, n: int = 5) -> dict:
        check(expr, tz); return {"next_runs": cron.upcoming(expr, tz, time.time(), max(1, min(n, 10)))}

    # ---- scheduler (run worker) ----
    # typing.List: in this class body `list` is the method above, and Python 3.12 evaluates annotations eagerly
    def fire_due(self, now: Optional[float] = None) -> List[str]:
        """Start a run for every due schedule this process wins; returns the run ids."""
        now = time.time() if now is None else now; started = []
        for s in self.schedules.due(now):
            try: nxt = self._next(s.cron, s.timezone, now)
            except AppError: nxt = None  # stored before a rule change; stop it below
            if not self.schedules.claim(s.id, s.next_run, nxt, now): continue  # another worker took it
            if self.workflows.get(s.workflow_id) is None:
                self.schedules.delete(s.id); log.info("schedule %s removed: workflow %s is gone", s.id, s.workflow_id); continue
            stop = "invalid" if nxt is None else None
            if self.access is not None and not self.access.may(s.workflow_id, s.owner, P.SHARE): stop = "access"
            if stop:
                self.schedules.set_fields(s.id, enabled=False, next_run=None, note=stop)
                log.warning("schedule %s turned off (%s)", s.id, stop); continue
            rid = uuid.uuid4().hex[:10]; inp = json.loads(s.input or "{}")
            self.runs.add(Run(id=rid, workflow_id=s.workflow_id, input=s.input, events="[]", status="queued", started=now, owner=s.owner, source="schedule"))
            self.jobs.enqueue({"run_id": rid, "workflow_id": s.workflow_id, "owner": s.owner, "input": inp, "callback_url": None, "token_id": None, "source": "schedule"})
            self.schedules.set_fields(s.id, last_run_id=rid); started.append(rid)
        return started
