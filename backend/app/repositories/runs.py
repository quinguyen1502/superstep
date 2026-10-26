import json
from typing import Optional
from sqlalchemy import delete, or_, select, update
from sqlalchemy.exc import IntegrityError
from ..models import Run
from ..models.database import Database

NOT_TEST = or_(Run.source.is_(None), Run.source != "test")  # every run but workflow test runs (TASK-0067)


class StaleLease(Exception):
    """A write carried an outdated fencing token: another worker claimed the run since (TASK-0021)."""
    fenced = True  # the engine re-raises it instead of reporting a node error


class RunRepository:
    def __init__(self, db: Database): self.db = db

    def add(self, run: Run, fence: Optional[int] = None) -> None:
        """Insert or update (a resumed run keeps its id). With `fence` (a queue job's lease generation) the row is
        only updated while it still carries that generation; otherwise StaleLease is raised. Only the attributes set
        on `run` are written (like merge), so columns the caller does not know about (callback_url) are kept."""
        with self.db.session() as s:
            if fence is None: s.merge(run); s.commit(); return
            vals = {c.key: getattr(run, c.key) for c in Run.__mapper__.column_attrs if c.key not in ("id", "lease_gen") and c.key in vars(run)}
            if s.execute(update(Run).where(Run.id == run.id, Run.lease_gen == fence).values(**vals)).rowcount != 1:
                s.rollback(); raise StaleLease(run.id)
            s.commit()

    def claim(self, rid: str, statuses: tuple[str, ...]) -> Optional[int]:
        """Atomically mark the run `running` and bump its fencing token (compare-and-set). Returns the new
        generation, or None when the run is not in one of `statuses` or another worker claimed it first."""
        with self.db.session() as s:
            row = s.execute(select(Run.status, Run.lease_gen).where(Run.id == rid)).first()
            if row is None or row.status not in statuses: return None
            gen = (row.lease_gen or 0) + 1
            q = update(Run).where(Run.id == rid, Run.status == row.status, Run.lease_gen == row.lease_gen).values(status="running", lease_gen=gen)
            if s.execute(q).rowcount != 1: s.rollback(); return None
            s.commit(); return gen

    def lease_gen(self, rid: str) -> Optional[int]:
        with self.db.session() as s: return s.scalar(select(Run.lease_gen).where(Run.id == rid))

    def get(self, rid: str) -> Optional[Run]:
        with self.db.session() as s:
            return s.get(Run, rid)

    def set_status(self, rid: str, status: str) -> None:
        with self.db.session() as s:
            s.execute(update(Run).where(Run.id == rid).values(status=status)); s.commit()

    def save_progress(self, rid: str, events: str, checkpoint: str, fence: Optional[int] = None) -> None:
        """Progress checkpoint of a running queue job (TASK-0020); only while it is still running. A kept answer is
        used up from here on (TASK-0127). Fenced (TASK-0021): raises StaleLease when another worker holds a newer generation."""
        with self.db.session() as s:
            q = update(Run).where(Run.id == rid, Run.status == "running")
            if fence is not None: q = q.where(Run.lease_gen == fence)
            if s.execute(q.values(events=events, checkpoint=checkpoint, resume_job=None)).rowcount != 1 and fence is not None:
                s.rollback()
                if s.scalar(select(Run.lease_gen).where(Run.id == rid)) != fence: raise StaleLease(rid)
                return
            s.commit()

    def keep_resume(self, job: dict) -> None:
        """Keep the answer to a waiting run until the resumed segment records progress or a result (TASK-0127)."""
        with self.db.session() as s:
            s.execute(update(Run).where(Run.id == job["run_id"], Run.status == "waiting").values(resume_job=json.dumps(job, ensure_ascii=False)))
            s.commit()

    def list_resumes(self, limit: int = 500) -> list[Run]:
        """Runs with a kept answer: still waiting (the job was never taken), or claimed with nothing recorded since."""
        with self.db.session() as s:
            return list(s.scalars(select(Run).where(Run.resume_job.is_not(None), Run.status.in_(("waiting", "running")))
                                  .order_by(Run.started).limit(limit)))

    def child_of(self, parent: str, step: str) -> Optional[Run]:
        """The child run a workflow tool call started (TASK-0134)."""
        with self.db.session() as s:
            return s.scalars(select(Run).where(Run.parent_run_id == parent, Run.parent_step == step)).first()

    def children(self, parent: str) -> list[Run]:
        with self.db.session() as s:
            return list(s.scalars(select(Run).where(Run.parent_run_id == parent).order_by(Run.started)))

    def add_child(self, run: Run) -> Run:
        """Insert a child run, or return the one another attempt inserted for the same call first."""
        with self.db.session() as s:
            try: s.add(run); s.commit(); return run
            except IntegrityError: s.rollback()
        found = self.child_of(run.parent_run_id, run.parent_step)
        if found is None: raise RuntimeError("child run insert failed")
        return found

    def list_waiting(self, owner: str, limit: int = 100) -> list[Run]:
        """Runs waiting for this user's answer; a workflow test answers its own (TASK-0067)."""
        with self.db.session() as s:
            return list(s.scalars(select(Run).where(Run.owner == owner, Run.status == "waiting", NOT_TEST).order_by(Run.started.desc()).limit(limit)))

    def list_unfinished(self, limit: int = 500) -> list[Run]:
        """Queued or running queue-job runs (every source except the editor's, whose rows are written when they end)."""
        with self.db.session() as s:
            return list(s.scalars(select(Run).where(Run.status.in_(("queued", "running")), Run.source.is_not(None), Run.source != "ui")
                                  .order_by(Run.started).limit(limit)))

    def list_waiting_before(self, cutoff: float, limit: int = 500) -> list[Run]:
        """Waiting runs (any owner) paused before `cutoff` (Run.ended = time it started waiting)."""
        with self.db.session() as s:
            return list(s.scalars(select(Run).where(Run.status == "waiting", Run.ended < cutoff).limit(limit)))

    def last_for_workflow(self, wid: str) -> Optional[Run]:
        with self.db.session() as s:
            return s.scalars(select(Run).where(Run.workflow_id == wid, NOT_TEST).order_by(Run.started.desc()).limit(1)).first()

    def list_for_workflow(self, wid: str, limit: int = 50, tests: bool = False) -> list[Run]:
        """tests: workflow test runs (TASK-0067) only; otherwise every other run."""
        with self.db.session() as s:
            q = select(Run).where(Run.workflow_id == wid, Run.source == "test" if tests else NOT_TEST)
            return list(s.scalars(q.order_by(Run.started.desc()).limit(limit)))

    def delete_for_workflow(self, wid: str) -> None:
        with self.db.session() as s:
            s.execute(delete(Run).where(Run.workflow_id == wid)); s.commit()
